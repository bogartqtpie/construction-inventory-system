// ================================
// POS PAGE CART & CHECKOUT LOGIC
// ================================
let cart = [];

// Find option text for material name
function findMaterialOption(id) {
    const opt = document.querySelector(`#material-select option[value="${id}"]`);
    return opt;
}

// Add item to cart
function addToCart(materialId, qty, price) {
    const existing = cart.find(c => c.material_id == materialId);
    if (existing) {
        existing.qty += qty;
        existing.price = price;
    } else {
        const opt = findMaterialOption(materialId);
        const text = opt ? opt.textContent : "Unknown";
        cart.push({ material_id: materialId, name: text, qty: qty, price: price });
    }
    renderCart();
}

// Render cart table
function renderCart() {
    const tbody = document.querySelector("#cart-table tbody");
    tbody.innerHTML = "";
    let total = 0;

    cart.forEach((c, idx) => {
        const subtotal = c.qty * c.price;
        total += subtotal;
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${c.name}</td>
            <td>${c.qty}</td>
            <td>₱${c.price.toFixed(2)}</td>
            <td>₱${subtotal.toFixed(2)}</td>
            <td><button class="btn btn-sm btn-danger" onclick="removeItem(${idx})">X</button></td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById("total").textContent = total.toFixed(2);
}

// Remove item from cart
function removeItem(idx) {
    cart.splice(idx, 1);
    renderCart();
}

// ================================
// EVENT LISTENERS
// ================================
document.addEventListener("DOMContentLoaded", function () {

    // ADD TO CART
    document.getElementById("add-to-cart").addEventListener("click", function () {
        const sel = document.getElementById("material-select");
        const mid = sel.value;
        if (!mid) {
            alert("Select material first!");
            return;
        }
        const qty = parseFloat(document.getElementById("qty").value) || 1;
        const price = parseFloat(document.getElementById("price").value) || 0;
        addToCart(mid, qty, price);
    });

    // CHECKOUT BUTTON
    const checkoutBtn = document.getElementById("checkoutBtn") || document.getElementById("checkout");
    checkoutBtn.addEventListener("click", async function () {
        if (cart.length === 0) {
            alert("Cart is empty!");
            return;
        }

        const total = parseFloat(document.getElementById("total").textContent);
        const payload = { items: cart, total: total };

        try {
            const response = await fetch("/checkout", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.success) {
                // ✅ Real checkout successful
                alert("✅ Checkout complete! Sale recorded successfully.");

                // Show low stock alert if applicable
                if (data.low && data.low.length > 0) {
                    alert("⚠️ Low stock:\n" + data.low.map(i => `${i.name} (${i.qty})`).join(", "));
                }

                // Reset cart and refresh
                cart = [];
                renderCart();
                setTimeout(() => location.reload(), 1000);

            } else {
                alert("❌ Checkout failed: " + (data.message || "Unknown error"));
            }

        } catch (e) {
            console.error(e);
            alert("⚠️ Network or server error while checking out. Check Flask logs.");
        }
    });
});
