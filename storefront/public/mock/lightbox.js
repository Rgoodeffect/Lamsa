/**
 * Stand-in for the Moamalat Lightbox script, used only when ERP_MOCK_ONLINE_PAYMENT=1.
 * It fires completeCallback with a payload shaped like the gateway's, so the storefront's payment
 * flow can be developed and tested without a merchant account. The real script is loaded from
 * Moamalat's own domain and the real payload is signed with the merchant secret key.
 */
window.Lightbox = {
  Checkout: {
    configure: {},
    showLightbox: function () {
      var c = window.Lightbox.Checkout.configure || {};
      setTimeout(function () {
        if (typeof c.completeCallback === "function") {
          c.completeCallback({
            Amount: String(c.AmountTrxn || 0),
            Currency: "434",
            MerchantReference: c.MerchantReference,
            NetworkReference: "MOCK-NETWORK",
            PaidThrough: "Card",
            PayerAccount: "4111********1111",
            PayerName: "MOCK PAYER",
            SystemReference: "MOCK-SYSTEM",
            TxnDate: c.TrxDateTime,
            SecureHash: "MOCK",
          });
        }
      }, 400);
    },
    closeLightbox: function () {},
  },
};
