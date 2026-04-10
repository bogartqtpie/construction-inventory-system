// call this when user clicks confirm/checkout
async function doCheckout(items) {
    // items must be an array of objects: { material_id: "1", qty: 2 }
    const payload = { items: items };

    console.log("Sending payload to /checkout:", payload);

    try {
        const res = await fetch("/checkout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        // show raw response text if parsing fails
        const text = await res.text();
        let data;
        try { data = JSON.parse(text); } catch (e) { data = null; }

        console.log("HTTP", res.status, "responseText:", text, "parsed:", data);

        if (!res.ok) {
            // show server-provided error if any
            const errMsg = data && (data.error || data.message) ? (data.error || data.message) : `HTTP ${res.status}`;
            alert("❌ Checkout failed: " + errMsg);
            return;
        }

        // success
        alert("✅ Checkout successful");
        // if server returned sale_id, redirect
        if (data && data.sale_id) {
            window.location.href = `/sales/${data.sale_id}`;
        } else {
            location.reload();
        }
    } catch (err) {
        console.error("Network/fetch error:", err);
        alert("⚠️ Network error: " + err.message);
    }
}
