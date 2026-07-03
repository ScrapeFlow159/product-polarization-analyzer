// admin_guard.js - Admin pages ke liye security guard
(function checkAdminAccess() {
    const token = localStorage.getItem('token');
    const role = localStorage.getItem('role');
    const username = localStorage.getItem('username');
    
    // Agar token nahi hai toh login karein
    if (!token) {
        alert('❌ Please login first.');
        window.location.href = '/login.html';
        return false;
    }
    
    // Agar Admin nahi hai toh dashboard pe bhejein
    if (role !== 'Admin') {
        alert('❌ Unauthorized access! Admin privileges required.\n\nYou are logged in as: ' + role);
        window.location.href = '/dashboard.html';
        return false;
    }
    
    // Access granted - log for audit
    console.log(`✅ Admin access granted: ${username} at ${new Date().toISOString()}`);
    return true;
})();