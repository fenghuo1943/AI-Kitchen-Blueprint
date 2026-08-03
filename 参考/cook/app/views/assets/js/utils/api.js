// 通用API请求
export async function apiRequest(url, method = 'GET', body = null, _retry = false) {

    try {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                Authorization: 'Bearer ' + localStorage.getItem('accessToken')
            }
        };

        if (body) {
            options.body = JSON.stringify(body);
        }
        const res = await fetch(url, options);
        // ⭐ 核心：先判断 HTTP 状态码
        if (res.status === 401) {
            return refreshToken(url, method, body, _retry);
        }
        const data = await res.json();
        if(data.code === 401){
            return refreshToken(url, method, body, _retry);
        }
        if (data.code !== 0) {
            //throw new Error(data.msg || '操作失败');
            //alert(data.msg || '操作失败');
        }
        return data;
    }
    catch (err) {
        console.error('API请求失败：', err + url);
        alert(err||'API请求失败');
        //throw err;
    }
}
async function refreshToken(url, method, body, _retry) {
    if (_retry) {
        logout();
        return;
    }
    const refreshToken = getToken('refreshToken');
    if (!refreshToken) {
        logout();
        return;
    }
    try {
        const refreshRes = await fetch('api/refresh', {
            method: 'GET',
            headers: {
                Authorization: 'Bearer ' + refreshToken
            }
        });
        if (!refreshRes.ok) {
            logout();
            return;
        }
        const result = await refreshRes.json();
        const newAccessToken = result.data?.accessToken;
        const newRefreshToken = result.data?.refreshToken;
        // ⭐ 防止后端返回异常
        if (!newAccessToken) {
            logout();
            return;
        }
        // 更新 token
        localStorage.setItem('accessToken', newAccessToken);
        localStorage.setItem('refreshToken', newRefreshToken);
        // ⭐ 重试请求（只允许一次）
        return apiRequest(url, method, body, true);
    } catch (err) {
        console.error('refresh失败:', err);
        logout();
    }
}
function logout() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    //alert('登录已过期，请重新登录');
    window.location.href =
        '/cook/auth?redirect=' +
        window.location.pathname +
        window.location.hash;
}
function getToken(key) {
    const val = localStorage.getItem(key);
    if (!val || val === 'undefined') return null;
    return val;
}
window.apiRequest = apiRequest;