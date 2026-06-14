// common.js - 全局通用功能

// ==========================================
// 1. 加载动画
// ==========================================

function showLoading(text = '加载中...') {
    let overlay = document.getElementById('loadingOverlay');
    
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div style="text-align: center;">
                <div class="loading-spinner"></div>
                <div class="loading-text"></div>
            </div>
        `;
        overlay.querySelector('.loading-text').textContent = text;
        document.body.appendChild(overlay);
    } else {
        const loadingText = overlay.querySelector('.loading-text');
        if (loadingText) loadingText.textContent = text;
    }
    
    overlay.classList.add('show');
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('show');
    }
}

// ==========================================
// 2. Toast 提示
// ==========================================

let toastContainer = null;

function initToastContainer() {
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
}

function showToast(message, type = 'info', duration = 3000) {
    initToastContainer();
    
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-times-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="toast-icon ${icons[type]}"></i>
        <div class="toast-message"></div>
        <button class="toast-close" onclick="closeToast(this.parentElement)">&times;</button>
    `;
    toast.querySelector('.toast-message').textContent = message;
    
    toastContainer.appendChild(toast);
    
    // 自动关闭
    if (duration > 0) {
        setTimeout(() => {
            closeToast(toast);
        }, duration);
    }
    
    return toast;
}

function closeToast(toast) {
    if (!toast || toast.classList.contains('hiding')) return;
    
    toast.classList.add('hiding');
    setTimeout(() => {
        if (toast.parentElement) {
            toast.parentElement.removeChild(toast);
        }
    }, 300);
}

// ==========================================
// 3. 统一错误处理
// ==========================================

function handleApiError(error, defaultMessage = '请求失败，请稍后重试') {
    console.error('API Error:', error);
    let message = defaultMessage;
    if (error instanceof Response) {
        message = `服务器错误 (${error.status})`;
    } else if (error instanceof TypeError && error.message.includes('fetch')) {
        message = '网络连接失败，请检查网络';
    } else if (error.message) {
        message = error.message;
    }
    showToast(message, 'error');
    return message;
}

// ==========================================
// 4. 图片预览
// ==========================================

function previewImage(input, previewId) {
    const preview = document.getElementById(previewId);
    if (!preview || !input || !input.files || !input.files[0]) return;
    
    const reader = new FileReader();
    
    reader.onload = function(e) {
        const img = preview.querySelector('img') || document.createElement('img');
        img.src = e.target.result;
        img.style.maxWidth = '100%';
        img.style.maxHeight = '200px';
        
        if (!preview.querySelector('img')) {
            preview.appendChild(img);
        }
    };
    
    reader.readAsDataURL(input.files[0]);
}

// ==========================================
// 5. 防抖和节流
// ==========================================

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ==========================================
// 6. 格式化工具
// ==========================================

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(date) {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ==========================================
// 7. 图片懒加载
// ==========================================

function lazyLoadImages() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
}

// ==========================================
// 8. 全局初始化
// ==========================================

document.addEventListener('DOMContentLoaded', function() {
    // 初始化 Toast 容器
    initToastContainer();
    
    // 初始化图片懒加载
    lazyLoadImages();
    
    // 添加全局错误处理
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
    });
    
    window.addEventListener('unhandledrejection', function(e) {
        console.error('Unhandled promise rejection:', e.reason);
    });
});

// 导出全局函数
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.showToast = showToast;
window.handleApiError = handleApiError;
window.previewImage = previewImage;
window.debounce = debounce;
window.throttle = throttle;
window.formatFileSize = formatFileSize;
window.formatDate = formatDate;
window.lazyLoadImages = lazyLoadImages;
