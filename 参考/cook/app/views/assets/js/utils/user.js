let userId = 0;

window.getProfile = async function getProfile() {
    
    const res = await apiRequest('api/profile');
    
    return await res;
}
window.userId = userId;