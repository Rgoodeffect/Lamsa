"""CLIP vision encoder through onnxruntime, running on the store's own server.

Nothing is sent to a third party: a customer's photo is encoded in this process and thrown away.

Setup on the server:

    ./env/bin/pip install onnxruntime pillow
    bench --site <site> set-config lamsa_image_model_path /home/frappe/models/clip-vision.onnx
    bench --site <site> set-config lamsa_image_model_name clip-vit-b-32-vision

Only the **vision** half of CLIP is needed — product images and the customer's photo go through the
same encoder — which is about half the download and half the memory of the full model.

The ONNX input and output names are read from the model file at load time rather than hard-coded,
because they differ between exports of the same architecture. The preprocessing, by contrast, is part
of CLIP itself and is fixed here: resize the short side to 224 (bicubic), centre-crop to 224x224,
convert to RGB, scale to 0..1, then normalise with CLIP's channel mean and standard deviation. Getting
that wrong does not error, it just quietly ruins the matches, so it is written out explicitly.
"""

import io
import threading

from store_core.providers.embeddings.base import EmbeddingError, ImageEmbedder
from store_core.services.settings import get_secret
from store_core.services.vectors import normalise

IMAGE_SIZE = 224
#: CLIP's own preprocessing constants; not tunable.
CLIP_MEAN = (0.48145466, 0.4578275, 0.40821073)
CLIP_STD = (0.26862954, 0.26130258, 0.27577711)
DEFAULT_MODEL_NAME = "clip-vit-b-32-vision"

_lock = threading.Lock()
_session = None
_io_names: tuple[str, str] | None = None


def model_path() -> str | None:
	return get_secret("lamsa_image_model_path")


class ClipOnnxEmbedder(ImageEmbedder):
	@property
	def name(self) -> str:
		return get_secret("lamsa_image_model_name") or DEFAULT_MODEL_NAME

	@property
	def dimensions(self) -> int:
		session, (_input_name, output_name) = _load()
		for output in session.get_outputs():
			if output.name != output_name:
				continue
			# [batch, dim]; a symbolic batch dimension comes back as a string, so keep the integers
			dims = [d for d in output.shape if isinstance(d, int)]
			if dims:
				return int(dims[-1])
		raise EmbeddingError("the model does not declare an output size")

	def is_available(self) -> bool:
		if not model_path():
			return False
		try:
			_load()
			return True
		except Exception:
			return False

	def embed(self, image_bytes: bytes) -> list[float]:
		session, (input_name, output_name) = _load()
		tensor = _preprocess(image_bytes)
		try:
			outputs = session.run([output_name], {input_name: tensor})
		except Exception as exc:
			raise EmbeddingError(f"the model could not encode the image: {exc}") from exc
		vector = _first_row(outputs[0])
		if not vector:
			raise EmbeddingError("the model returned an empty vector")
		return normalise(vector)


def _load():
	"""The onnxruntime session, created once per process.

	Loading costs hundreds of milliseconds and a few hundred megabytes, so it is deliberately shared
	and lazy: a worker that never embeds anything never pays for it.
	"""
	global _session, _io_names
	if _session is not None and _io_names is not None:
		return _session, _io_names
	with _lock:
		if _session is None or _io_names is None:
			path = model_path()
			if not path:
				raise EmbeddingError("lamsa_image_model_path is not set")
			try:
				import onnxruntime
			except ImportError as exc:
				raise EmbeddingError("onnxruntime is not installed in the bench environment") from exc
			try:
				session = onnxruntime.InferenceSession(path, providers=["CPUExecutionProvider"])
			except Exception as exc:
				raise EmbeddingError(f"could not load the model at {path}: {exc}") from exc
			# Read the real names off the model instead of assuming an export's conventions.
			_session = session
			_io_names = (session.get_inputs()[0].name, session.get_outputs()[0].name)
	return _session, _io_names


def _preprocess(image_bytes: bytes):
	"""Image bytes -> a 1x3x224x224 float32 NCHW tensor, preprocessed the way CLIP expects."""
	try:
		import numpy
		from PIL import Image
	except ImportError as exc:
		raise EmbeddingError("pillow and numpy are required to encode images") from exc

	try:
		image = Image.open(io.BytesIO(image_bytes))
		image.load()
		image = image.convert("RGB")
	except Exception as exc:
		raise EmbeddingError("that file is not a readable image") from exc

	image = _resize_short_side(image, IMAGE_SIZE)
	image = _centre_crop(image, IMAGE_SIZE)

	array = numpy.asarray(image, dtype=numpy.float32) / 255.0
	array = (array - numpy.array(CLIP_MEAN, dtype=numpy.float32)) / numpy.array(CLIP_STD, dtype=numpy.float32)
	# HWC -> NCHW
	return numpy.ascontiguousarray(array.transpose(2, 0, 1)[None, ...], dtype=numpy.float32)


def _resize_short_side(image, size: int):
	from PIL import Image

	width, height = image.size
	if width == 0 or height == 0:
		raise EmbeddingError("that image has no size")
	scale = size / min(width, height)
	target = (max(1, round(width * scale)), max(1, round(height * scale)))
	return image.resize(target, Image.BICUBIC)


def _centre_crop(image, size: int):
	width, height = image.size
	left = max(0, (width - size) // 2)
	top = max(0, (height - size) // 2)
	return image.crop((left, top, left + size, top + size))


def _first_row(output) -> list[float]:
	"""Take the single image's vector out of whatever shape the model returned."""
	values = output
	while hasattr(values, "shape") and len(getattr(values, "shape", ())) > 1:
		values = values[0]
	return [float(x) for x in values]
