const cart = [];
let products = [];

const money = n => "₹" + Number(n).toFixed(2);

async function loadProducts() {
  const grid = document.getElementById("product-grid");
  if (!grid) return;
  try {
    const response = await fetch("/api/products");
    products = await response.json();
    grid.innerHTML = products.map(p => `
      <article class="product-card">
        <div class="product-image"><img src="${escapeHtml(p.image)}" alt="${escapeHtml(p.name)}" loading="lazy"></div>
        <div class="product-info">
          <span class="category">${escapeHtml(p.category)}</span>
          <h3>${escapeHtml(p.name)}</h3>
          <p>${escapeHtml(p.description)}</p>
          <label class="variant-label">Pack / variant
            <select id="variant-${p.id}">${p.variants.map(v => `<option value="${escapeHtml(v.name)}" data-price="${v.price ?? ""}">${escapeHtml(v.name)}${v.price == null ? " · Price on request" : " · " + money(v.price)}</option>`).join("")}</select>
          </label>
          <button class="button button-outline full" onclick="addToCart('${p.id}')">Add to cart</button>
        </div>
      </article>`).join("");
  } catch (e) {
    grid.innerHTML = '<p class="muted">Could not load products. Please refresh the page.</p>';
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function addToCart(productId) {
  const product = products.find(p => p.id === productId);
  const select = document.getElementById(`variant-${productId}`);
  const variant = select.value;
  const selected = product.variants.find(v => v.name === variant);
  const existing = cart.find(i => i.product_id === productId && i.variant === variant);
  if (existing) existing.quantity += 1;
  else cart.push({product_id: productId, product_name: product.name, variant, quantity: 1, unit_price: selected.price});
  renderCart();
  document.getElementById("cart").scrollIntoView({behavior:"smooth"});
}

function changeQty(index, delta) {
  cart[index].quantity += delta;
  if (cart[index].quantity <= 0) cart.splice(index, 1);
  renderCart();
}

function renderCart() {
  const holder = document.getElementById("cart-items");
  if (!holder) return;
  const count = cart.reduce((n, i) => n + i.quantity, 0);
  document.getElementById("cart-count").textContent = count;
  if (!cart.length) {
    holder.innerHTML = '<p class="muted">Your cart is empty.</p>';
    document.getElementById("cart-total").textContent = "To be confirmed";
    return;
  }
  let total = 0, hasUnpriced = false;
  holder.innerHTML = cart.map((i, idx) => {
    if (i.unit_price == null) hasUnpriced = true; else total += i.unit_price * i.quantity;
    return `<div class="cart-row"><div><strong>${escapeHtml(i.product_name)}</strong><small>${escapeHtml(i.variant)} · ${i.unit_price == null ? "Price TBC" : money(i.unit_price)}</small></div><div class="quantity"><button type="button" onclick="changeQty(${idx},-1)">−</button><b>${i.quantity}</b><button type="button" onclick="changeQty(${idx},1)">+</button></div></div>`;
  }).join("");
  document.getElementById("cart-total").textContent = hasUnpriced ? "To be confirmed" : money(total);
}

document.addEventListener("DOMContentLoaded", () => {
  loadProducts();
  const form = document.getElementById("checkout-form");
  if (!form) return;
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const message = document.getElementById("checkout-message");
    if (!cart.length) { message.textContent = "Please add at least one product to your cart."; return; }
    const formData = new FormData(form);
    const payload = {
      name: formData.get("name"), phone: formData.get("phone"),
      address: formData.get("address"), notes: formData.get("notes"),
      items: cart.map(i => ({product_id:i.product_id, variant:i.variant, quantity:i.quantity}))
    };
    const button = form.querySelector("button[type=submit]");
    button.disabled = true; button.textContent = "Saving your order…";
    message.textContent = "";
    try {
      const response = await fetch("/api/orders", {
        method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not save your order.");
      sessionStorage.setItem("lastOrderNumber", result.order_number);
      window.location.href = result.whatsapp_url;
    } catch (error) {
      message.textContent = error.message;
      button.disabled = false; button.textContent = "Save order & continue to WhatsApp";
    }
  });
});
