const CART_STORAGE_KEY = "rhf_cart_v1";
let products = [];

const money = (n) => "₹" + Number(n).toFixed(2);

function loadCart() {
  try {
    const raw = JSON.parse(localStorage.getItem(CART_STORAGE_KEY) || "[]");
    return Array.isArray(raw) ? raw : [];
  } catch {
    return [];
  }
}

function saveCart(items) {
  localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

function getEffectivePrice(product, variantName, qty, selectedAttrs = {}) {
  const variants = Array.isArray(product.variants) ? product.variants : [];
  const variantObj = variants.find((v) => v.name === variantName) || variants[0] || {};
  const pack500 = variants.find((v) => v.name === "500g");

  let basePrice = variantObj.price;
  let applied500Bundle = false;

  if (variantName === "250g" && qty === 2 && pack500 && pack500.price != null) {
    basePrice = pack500.price;
    applied500Bundle = true;
  }

  let deltaSum = 0;
  let deltaUnpriced = false;
  const attrsList = Array.isArray(product.attributes) ? product.attributes : [];

  for (const attr of attrsList) {
    const chosenVal = selectedAttrs[attr.key];
    const options = Array.isArray(attr.options) ? attr.options : [];
    const optObj = options.find((o) => o.value === chosenVal) || options[0];

    if (optObj) {
      if (optObj.price_delta === null || optObj.price_delta === undefined) {
        deltaUnpriced = true;
      } else {
        deltaSum += Number(optObj.price_delta) || 0;
      }
    }
  }

  if (basePrice === null || basePrice === undefined || deltaUnpriced) {
    return { lineTotal: null, unitDisplayPrice: null, applied500Bundle };
  }

  const perItemOrBundle = Number((Number(basePrice) + deltaSum).toFixed(2));

  if (applied500Bundle) {
    return {
      lineTotal: perItemOrBundle,
      unitDisplayPrice: Number((perItemOrBundle / 2).toFixed(2)),
      applied500Bundle: true,
    };
  }

  return {
    lineTotal: Number((perItemOrBundle * qty).toFixed(2)),
    unitDisplayPrice: perItemOrBundle,
    applied500Bundle: false,
  };
}

function computeUnitAndSubtotal(product, variantName, selectedAttrs, qty) {
  const { lineTotal, unitDisplayPrice, applied500Bundle } = getEffectivePrice(
    product,
    variantName,
    qty,
    selectedAttrs
  );
  return { unitPrice: unitDisplayPrice, subtotal: lineTotal, applied500Bundle };
}

function updateHeaderCart(cart = loadCart()) {
  const countEl = document.getElementById("cart-count");
  const totalQty = cart.reduce((sum, item) => sum + (Number(item.quantity) || 0), 0);

  if (countEl) countEl.textContent = String(totalQty);

  const cartLink = document.querySelector(".cart-link");
  if (cartLink) {
    cartLink.classList.toggle("has-items", totalQty > 0);
  }

  const feedbackBar = document.getElementById("cart-feedback-bar");
  const orderBtn = document.getElementById("place-order-cta");

  if (orderBtn) {
    orderBtn.textContent = "Order";
    orderBtn.setAttribute("href", "/cart");
  }
  if (feedbackBar && totalQty > 0) {
    feedbackBar.hidden = false;
  }
}

function highlightCartAndShowOrderButton(addedLabel) {
  const cartLink = document.querySelector(".cart-link");
  if (cartLink) {
    cartLink.classList.remove("cart-link--added");
    void cartLink.offsetWidth;
    cartLink.classList.add("cart-link--added", "is-highlighted", "has-items");
  }

  const feedbackBar = document.getElementById("cart-feedback-bar");
  const highlightText = document.getElementById("cart-added-highlight");
  const orderBtn = document.getElementById("place-order-cta");

  if (orderBtn) {
    orderBtn.textContent = "Order";
    orderBtn.setAttribute("href", "/cart");
  }
  if (highlightText) {
    highlightText.textContent = `${addedLabel} added to cart.`;
  }
  if (feedbackBar) {
    feedbackBar.hidden = false;
    feedbackBar.classList.add("is-highlighted");
  }
}

async function loadProducts() {
  const grid = document.getElementById("product-grid");
  if (!grid) return;

  try {
    const response = await fetch("/api/products");
    if (!response.ok) throw new Error("Failed to load products");

    products = await response.json();
    grid.innerHTML = "";

    products.forEach((p) => {
      const minQty = Math.max(1, Number(p.min_qty) || 1);
      const variants = Array.isArray(p.variants) ? p.variants : [];
      const attributes = Array.isArray(p.attributes) ? p.attributes : [];

      const variantOptionsHtml = variants
        .map((v) => {
          const priceLabel = v.price == null ? "Price on request" : money(v.price);
          return `<option value="${escapeHtml(v.name)}">${escapeHtml(v.name)} · ${escapeHtml(priceLabel)}</option>`;
        })
        .join("");

      const attrFieldsHtml = attributes
        .map((attr) => {
          const optsHtml = (attr.options || [])
            .map((opt) => {
              const delta = Number(opt.price_delta) || 0;
              const deltaSuffix = delta > 0 ? ` (+${money(delta)})` : "";
              return `<option value="${escapeHtml(opt.value)}">${escapeHtml(opt.value)}${escapeHtml(deltaSuffix)}</option>`;
            })
            .join("");

          return `
            <label class="variant-label">
              ${escapeHtml(attr.label)}
              <select class="attr-select" data-attr-key="${escapeHtml(attr.key)}">${optsHtml}</select>
            </label>
          `;
        })
        .join("");

      const cardNoteHtml = p.card_note
        ? `<div class="card-meta-note">${escapeHtml(p.card_note)}</div>`
        : "";

      const card = document.createElement("article");
      card.className = "product-card";
      card.dataset.productId = p.id;
      card.innerHTML = `
        <div class="product-image">
          <img src="${escapeHtml(p.image)}" alt="${escapeHtml(p.name)}" loading="lazy">
        </div>
        <div class="product-info">
          <span class="category">${escapeHtml(p.category)} · Min qty: ${minQty}</span>
          <h3>${escapeHtml(p.name)}</h3>
          <p>${escapeHtml(p.description)}</p>
          ${cardNoteHtml}
          <label class="variant-label">
            Pack / variant
            <select class="variant-select">${variantOptionsHtml}</select>
          </label>
          ${attrFieldsHtml}
          <label class="variant-label">
            Quantity (min ${minQty})
            <div class="quantity product-qty-control" style="display:flex; align-items:center; gap:8px; margin-top:6px;">
              <button type="button" class="qty-minus" aria-label="Decrease quantity" style="padding:8px 14px; font-size:18px; cursor:pointer;">−</button>
              <input type="number" class="qty-input" min="${minQty}" max="50" value="${minQty}" inputmode="numeric" style="text-align:center; width:64px;">
              <button type="button" class="qty-plus" aria-label="Increase quantity" style="padding:8px 14px; font-size:18px; cursor:pointer;">+</button>
            </div>
          </label>
          <div class="product-subtotal-row">
            <span>Subtotal (base delivery incl.)</span>
            <strong class="line-subtotal">To be confirmed</strong>
          </div>
          <button type="button" class="button button-outline full add-to-cart-btn">Add to cart</button>
          <div class="added-status" hidden>Added to cart ✓</div>
        </div>
      `;

      const variantSelect = card.querySelector(".variant-select");
      const qtyInput = card.querySelector(".qty-input");
      const minusBtn = card.querySelector(".qty-minus");
      const plusBtn = card.querySelector(".qty-plus");
      const subtotalEl = card.querySelector(".line-subtotal");
      const addBtn = card.querySelector(".add-to-cart-btn");
      const addedStatusEl = card.querySelector(".added-status");

      function readSelectedAttributes() {
        const chosen = {};
        card.querySelectorAll(".attr-select").forEach((sel) => {
          chosen[sel.dataset.attrKey] = sel.value;
        });
        return chosen;
      }

      function refreshSubtotal() {
        let qty = parseInt(qtyInput.value, 10);
        if (Number.isNaN(qty) || qty < minQty) {
          qty = minQty;
          qtyInput.value = String(minQty);
        } else if (qty > 50) {
          qty = 50;
          qtyInput.value = "50";
        }

        const { subtotal } = computeUnitAndSubtotal(
          p,
          variantSelect.value,
          readSelectedAttributes(),
          qty
        );
        subtotalEl.textContent = subtotal == null ? "To be confirmed" : money(subtotal);
      }

      minusBtn.addEventListener("click", (event) => {
        event.preventDefault();
        const current = parseInt(qtyInput.value, 10) || minQty;
        qtyInput.value = String(Math.max(minQty, current - 1));
        refreshSubtotal();
      });

      plusBtn.addEventListener("click", (event) => {
        event.preventDefault();
        const current = parseInt(qtyInput.value, 10) || minQty;
        qtyInput.value = String(Math.min(50, current + 1));
        refreshSubtotal();
      });

      variantSelect.addEventListener("change", refreshSubtotal);
      qtyInput.addEventListener("input", refreshSubtotal);
      qtyInput.addEventListener("change", refreshSubtotal);

      card.querySelectorAll(".attr-select").forEach((sel) => {
        sel.addEventListener("change", refreshSubtotal);
      });

      addBtn.addEventListener("click", (event) => {
        event.preventDefault();
        refreshSubtotal();

        const qty = Math.max(minQty, Math.min(50, parseInt(qtyInput.value, 10) || minQty));
        const packVariant = variantSelect.value;
        const selectedAttrs = readSelectedAttributes();
        const { unitPrice } = computeUnitAndSubtotal(p, packVariant, selectedAttrs, qty);

        const attrValues = Object.values(selectedAttrs).filter(Boolean);
        const fullVariantLabel = attrValues.length
          ? `${packVariant} (${attrValues.join(", ")})`
          : packVariant;

        const lineKey = `${p.id}::${fullVariantLabel}`;
        const cart = loadCart();
        const existing = cart.find((item) => item.lineKey === lineKey);

        if (existing) {
          existing.quantity = Math.min(50, (Number(existing.quantity) || 0) + qty);
          existing.unit_price = unitPrice;
          existing.min_qty = minQty;
        } else {
          cart.push({
            lineKey,
            product_id: p.id,
            product_name: p.name,
            variant: fullVariantLabel,
            pack_variant: packVariant,
            attributes: selectedAttrs,
            quantity: qty,
            min_qty: minQty,
            unit_price: unitPrice,
          });
        }

        saveCart(cart);
        updateHeaderCart(cart);

        card.classList.add("is-added", "cart-highlighted");
        addBtn.classList.add("is-added");

        if (addedStatusEl) {
          addedStatusEl.hidden = false;
          addedStatusEl.textContent = `Added to cart ✓ (${fullVariantLabel} × ${qty})`;
        }

        highlightCartAndShowOrderButton(`${p.name} — ${fullVariantLabel}`);
      });

      refreshSubtotal();
      grid.appendChild(card);
    });
  } catch {
    grid.innerHTML = "Could not load products. Please refresh the page.";
  }
}

function changeQty(index, delta) {
  const cart = loadCart();
  const item = cart[index];
  if (!item) return;

  const minQty = Math.max(1, Number(item.min_qty) || 1);
  const nextQty = (Number(item.quantity) || minQty) + delta;

  if (nextQty < minQty) {
    cart.splice(index, 1);
  } else {
    item.quantity = Math.min(50, nextQty);
  }

  saveCart(cart);
  renderCart();
}

function clearCart() {
  saveCart([]);
  renderCart();
}

function renderCart() {
  const holder = document.getElementById("cart-items");
  const cart = loadCart();
  updateHeaderCart(cart);

  if (!holder) return;

  const totalEl = document.getElementById("cart-total");
  const checkoutForm = document.getElementById("checkout-form");
  const submitBtn = checkoutForm ? checkoutForm.querySelector('button[type="submit"]') : null;
  const clearBtn = document.getElementById("clear-cart-btn");

  if (clearBtn) {
    clearBtn.disabled = cart.length === 0;
  }

  if (!cart.length) {
    holder.innerHTML = "Your cart is empty. Browse products to add items.";
    if (totalEl) totalEl.textContent = "To be confirmed";
    if (submitBtn) submitBtn.disabled = true;
    return;
  }

  if (submitBtn) submitBtn.disabled = false;

  let total = 0;
  let hasUnpriced = false;

  holder.innerHTML = cart
    .map((item, idx) => {
      const minQty = Math.max(1, Number(item.min_qty) || 1);
      const qty = Math.max(minQty, Number(item.quantity) || minQty);
      const packName = item.pack_variant || item.variant;
      const catalogProduct = products.find((p) => p.id === item.product_id);

      let lineSub = null;
      let unitPrice = item.unit_price == null ? null : Number(item.unit_price);
      let bundleNote = "";

      if (catalogProduct) {
        const calc = getEffectivePrice(catalogProduct, packName, qty, item.attributes || {});
        lineSub = calc.lineTotal;
        unitPrice = calc.unitDisplayPrice;
        if (calc.applied500Bundle) {
          bundleNote = " · 500g pack rate applied";
        }
      } else if (unitPrice != null) {
        lineSub = Number((unitPrice * qty).toFixed(2));
      }

      let lineSubText = "Price TBC";
      if (lineSub != null) {
        total = Number((total + lineSub).toFixed(2));
        lineSubText = money(lineSub);
      } else {
        hasUnpriced = true;
      }

      const unitText = unitPrice == null ? "Price TBC" : `${money(unitPrice)} each`;

      return `
        <div class="cart-row">
          <div>
            <strong>${escapeHtml(item.product_name)}</strong>
            <small>${escapeHtml(item.variant)} · ${escapeHtml(unitText)}${escapeHtml(bundleNote)} · Min qty: ${minQty} · Line total: ${escapeHtml(lineSubText)}</small>
          </div>
          <div class="quantity">
            <button type="button" onclick="changeQty(${idx}, -1)" aria-label="Decrease quantity">−</button>
            <b>${qty}</b>
            <button type="button" onclick="changeQty(${idx}, 1)" aria-label="Increase quantity">+</button>
          </div>
        </div>
      `;
    })
    .join("");

  if (totalEl) {
    totalEl.textContent = hasUnpriced ? "To be confirmed" : money(total);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  updateHeaderCart();
  loadProducts();
  renderCart();

  const clearBtn = document.getElementById("clear-cart-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", clearCart);
  }

  const form = document.getElementById("checkout-form");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const currentCart = loadCart();
    const message = document.getElementById("checkout-message");

    if (!currentCart.length) {
      if (message) message.textContent = "Please add at least one product to your cart.";
      return;
    }

    const formData = new FormData(form);
    const payload = {
      name: String(formData.get("name") || "").trim(),
      phone: String(formData.get("phone") || "").trim(),
      address: String(formData.get("address") || "").trim(),
      notes: String(formData.get("notes") || "").trim(),
      items: currentCart.map((i) => ({
        product_id: i.product_id,
        variant: i.pack_variant || i.variant,
        attributes: i.attributes || {},
        quantity: i.quantity,
      })),
    };

    const button = form.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = true;
      button.textContent = "Saving your order…";
    }
    if (message) message.textContent = "";

    try {
      const response = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || "Could not save your order.");
      }

      saveCart([]);
      updateHeaderCart([]);
      sessionStorage.setItem("lastOrderNumber", result.order_number);
      window.location.href = result.whatsapp_url;
    } catch (error) {
      if (message) message.textContent = error.message;
      if (button) {
        button.disabled = false;
        button.textContent = "Save order & continue to WhatsApp";
      }
    }
  });
});
