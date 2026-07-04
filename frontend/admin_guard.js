// admin_guard.js
(function() {
    // Page ko turant hide kar dein taake unauthorized user ko kuch na dikhe
    document.documentElement.style.visibility = 'hidden';

    // Window load hone par check karein (taki localStorage access sahi ho)
    window.addEventListener('DOMContentLoaded', () => {
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('role');

        if (!token) {
            window.location.href = '/login.html';
            return;
        }

        if (role !== 'Admin') {
            // Alert ki jagah direct unauthorized access message
            document.body.innerHTML = `
                <div style="display:flex; justify-content:center; align-items:center; height:100vh; flex-direction:column; font-family:sans-serif;">
                    <h1 style="color:#dc3545;"><i class="fas fa-lock"></i> 403 - Access Denied</h1>
                    <p>Aapke paas is page ko dekhne ki ijazat nahi hai.</p>
                    <a href="/dashboard.html" class="btn btn-primary">Dashboard par wapas jayein</a>
                </div>
            `;
            document.documentElement.style.visibility = 'visible';
            return;
        }

        // Agar Admin hai, toh content visible kar dein
        document.documentElement.style.visibility = 'visible';
    });
})();