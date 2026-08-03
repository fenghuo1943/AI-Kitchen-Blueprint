/**
 * Toast 轻提示模块
 * 使用方式:
 * Toast.show('成功');
 * Toast.success('操作成功');
 * Toast.error('操作失败');
 */

window.Toast = window.Toast || (function () {

    let container = null;

    function createContainer() {
        if (container) return;

        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    function show(message, type = 'default', duration = 2000) {
        createContainer();

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerText = message;

        container.appendChild(toast);

        // 触发动画
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        // 自动消失
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    return {
        show,
        success(msg, duration) {
            show(msg, 'success', duration);
        },
        error(msg, duration) {
            show(msg, 'error', duration);
        }
    };

})();