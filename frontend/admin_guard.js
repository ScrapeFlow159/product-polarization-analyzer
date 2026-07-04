(function() {
    // 1. Page ko hide rakho taake content na dikhe
    document.documentElement.style.visibility = 'hidden';

    window.addEventListener('DOMContentLoaded', () => {
        const role = localStorage.getItem('role');

        if (role !== 'Admin') {
            // Agar Admin nahi hai, toh content ko replace kardo Error Message se
            document.body.innerHTML = `
                <div style="text-align:center; padding-top:100px; font-family:sans-serif;">
                    <h1 style="color:red;">❌ Unauthorized Access</h1>
                    <p>You dont have access to Admin panel.</p>
                    <a href="/dashboard.html" style="font-size:18px;">Redirect to dashboard</a>
                </div>
            `;
            // Message dikha do
            document.documentElement.style.visibility = 'visible';
            return;
        }

        // Agar Admin hai, toh visibility normal kar do
        document.documentElement.style.visibility = 'visible';
    });
})();