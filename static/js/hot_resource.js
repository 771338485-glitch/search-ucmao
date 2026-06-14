// hot_resource.js 精简版

// ==========================================
// 1. 全局变量与配置
// ==========================================
let currentPage = 1;
const pageSize = 25;
let totalPages = 1;
let resourcesData = [];

// ==========================================
// 2. DOM 元素获取
// ==========================================
const searchInput = document.getElementById('searchInput');
const resourcesTableBody = document.getElementById('resourcesTableBody');
const pagination = document.getElementById('pagination');

// 模态框与表单
const addResourceForm = document.getElementById('addResourceForm');
const editResourceForm = document.getElementById('editResourceForm');
const batchAddResourceForm = document.getElementById('batchAddResourceForm');

// 按钮
const saveResourceBtn = document.getElementById('saveResourceBtn');
const updateResourceBtn = document.getElementById('updateResourceBtn');
const batchSaveResourceBtn = document.getElementById('batchSaveResourceBtn');

// Cookie 配置相关元素
const cookieConfigModal = document.getElementById('cookieConfigModal');
const saveCookieConfigBtn = document.getElementById('saveCookieConfigBtn');
const baiduCookieInput = document.getElementById('baiduCookie');
const quarkCookieInput = document.getElementById('quarkCookie');

// ==========================================
// 3. 核心工具函数
// ==========================================

// 网盘匹配函数
function matchNetdiskLink(link) {
    if (!link) return "其他";
    const netdiskRules = [
        ["百度网盘", /(?:https?:\/\/)?(?:pan\.baidu\.com|bdpan\.com|baiduyun\.com)\//i],
        ["夸克网盘", /(?:https?:\/\/)?pan\.quark\.cn\//i],
        ["迅雷网盘", /(?:https?:\/\/)?pan\.xunlei\.com\//i],
        ["UC网盘", /(?:https?:\/\/)?(?:pan\.uc\.cn|drive\.uc\.cn)\//i],
        ["悟空网盘", /(?:https?:\/\/)?pan\.wkbrowser\.com\//i],
        ["快兔网盘", /(?:https?:\/\/)?(?:diskyun\.com|www\.diskyun\.com)\//i],
        ["115网盘", /(?:https?:\/\/)?(?:115\.com|115pan\.com|115cdn\.com|anxia\.com)\//i],
        ["阿里云盘", /(?:https?:\/\/)?(?:drive\.aliyun\.com|aliyundrive\.com|alipan\.com)\//i],
        ["天翼云盘", /(?:https?:\/\/)?cloud\.189\.cn\//i],
        ["移动云盘", /(?:https?:\/\/)?(?:pan\.10086\.cn|caiyun\.139\.com|yun\.139\.com)\//i],
        ["联通云盘", /(?:https?:\/\/)?pan\.wo\.cn\//i],
        ["123云盘", /(?:https?:\/\/)?(?:123pan\.com|123\d{3}\.com)\//i],
        ["PikPak", /(?:https?:\/\/)?(?:www\.)?pikpak\.com\//i],
        ["磁力链接", /^magnet:\?xt=urn:btih:/i],
        ["迅雷链接", /thunder:\/\/[A-Za-z0-9+\/=]+/i],
        ["电驴链接", /^ed2k:\/\//i]
    ];

    const linkLower = link.trim().toLowerCase();
    for (const [name, pattern] of netdiskRules) {
        if (pattern.test(linkLower)) {
            return name;
        }
    }
    return "其他";
}

// 显示 Toast 消息
function showToast(message, type = 'success') {
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
    toastContainer.style.zIndex = '9999';
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'danger' ? 'danger' : type === 'warning' ? 'warning' : 'success'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    document.body.appendChild(toastContainer);
    
    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toastContainer);
    });
}

// 确认对话框
async function showConfirm(message, type = 'primary') {
    return new Promise((resolve) => {
        const confirmModal = document.createElement('div');
        confirmModal.className = 'modal fade';
        confirmModal.setAttribute('tabindex', '-1');
        confirmModal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">确认操作</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p>${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-${type}" id="confirmModalOkBtn">确定</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(confirmModal);
        const modal = new bootstrap.Modal(confirmModal);
        modal.show();
        
        document.getElementById('confirmModalOkBtn').addEventListener('click', () => {
            modal.hide();
            resolve(true);
        });
        
        confirmModal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(confirmModal);
            resolve(false);
        });
    });
}

// ==========================================
// 4. 数据加载与渲染
// ==========================================

async function loadResources() {
    const searchKeyword = searchInput ? searchInput.value.trim() : '';
    
    if (resourcesTableBody) {
        resourcesTableBody.innerHTML = '<tr class="loading"><td colspan="7"></td></tr>';
    }

    try {
        const url = `/api/resources?page=${currentPage}&page_size=${pageSize}&search=${encodeURIComponent(searchKeyword)}`;
        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            resourcesData = data.data.items;
            totalPages = data.data.total_pages;
            renderTable();
            renderPagination();
        } else {
            showToast('加载资源失败: ' + (data.message || '未知错误'), 'danger');
            if (resourcesTableBody) {
                resourcesTableBody.innerHTML = '<tr><td colspan="7" class="text-center py-5">加载失败，请重试</td></tr>';
            }
        }
    } catch (error) {
        console.error('加载资源失败:', error);
        showToast('网络请求失败，请检查服务状态', 'danger');
        if (resourcesTableBody) {
            resourcesTableBody.innerHTML = '<tr><td colspan="7" class="text-center py-5">网络错误，请检查网络连接</td></tr>';
        }
    }
}

function renderTable() {
    if (!resourcesTableBody) return;
    
    resourcesTableBody.innerHTML = '';

    if (!resourcesData || resourcesData.length === 0) {
        const emptyRow = document.createElement('tr');
        emptyRow.innerHTML = '<td colspan="7" class="text-center py-5">暂无数据</td>';
        resourcesTableBody.appendChild(emptyRow);
        return;
    }

    resourcesData.forEach((resource, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${resource.id}</td>
            <td title="${resource.name}">${resource.name}</td>
            <td><a href="${resource.share_link}" target="_blank" class="text-truncate d-inline-block" style="max-width: 250px;">${resource.share_link}</a></td>
            <td>${resource.cloud_name || '-'}</td>
            <td>${resource.type || '-'}</td>
            <td>${resource.is_replaced ? '<span class="badge bg-success">已同步</span>' : '-'}</td>
            <td class="action-buttons d-flex justify-content-center align-items-center">
                <button class="btn btn-secondary btn-sm copy-btn me-2" data-id="${resource.id}" title="复制链接">
                    <i class="fas fa-copy"></i> 复制
                </button>
                <div class="dropdown">
                    <button class="btn btn-sm btn-secondary dropdown-toggle" type="button"
                        data-bs-toggle="dropdown" aria-expanded="false" title="更多操作">
                        <i class="fas fa-ellipsis-v"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li>
                            <a class="dropdown-item edit-btn" href="javascript:void(0)" data-id="${resource.id}">
                                <i class="fas fa-edit me-2"></i> 编辑
                            </a>
                        </li>
                        <li><hr class="dropdown-divider"></li>
                        <li>
                            <a class="dropdown-item text-danger delete-btn" href="javascript:void(0)" data-id="${resource.id}">
                                <i class="fas fa-trash me-2"></i> 删除
                            </a>
                        </li>
                    </ul>
                </div>
            </td>
        `;
        row.style.animationDelay = `${index * 0.1}s`;
        resourcesTableBody.appendChild(row);
    });

    bindActionEvents();
}

function renderPagination() {
    if (!pagination) return;
    pagination.innerHTML = '';

    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#" data-page="${currentPage - 1}">&laquo;</a>`;
    pagination.appendChild(prevLi);

    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);

    if (startPage > 1) {
        pagination.appendChild(createPageItem(1));
        if (startPage > 2) pagination.appendChild(createEllipsis());
    }

    for (let i = startPage; i <= endPage; i++) {
        pagination.appendChild(createPageItem(i));
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) pagination.appendChild(createEllipsis());
        pagination.appendChild(createPageItem(totalPages));
    }

    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages || totalPages === 0 ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#" data-page="${currentPage + 1}">&raquo;</a>`;
    pagination.appendChild(nextLi);
}

function createPageItem(page) {
    const li = document.createElement('li');
    li.className = `page-item ${page === currentPage ? 'active' : ''}`;
    li.innerHTML = `<a class="page-link" href="#" data-page="${page}">${page}</a>`;
    return li;
}

function createEllipsis() {
    const li = document.createElement('li');
    li.className = 'page-item disabled';
    li.innerHTML = '<span class="page-link">...</span>';
    return li;
}

// ==========================================
// 5. 交互事件处理
// ==========================================

function bindActionEvents() {
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', () => editResource(parseInt(btn.getAttribute('data-id'))));
    });
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteResource(parseInt(btn.getAttribute('data-id'))));
    });
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', () => copyResource(parseInt(btn.getAttribute('data-id'))));
    });
}

function copyResource(id) {
    const resource = resourcesData.find(r => r.id === id);
    if (!resource) return;

    const copyContent = `标题: ${resource.name}\n链接: ${resource.share_link}\n提取码: ${resource.code || '无'}`;
    navigator.clipboard.writeText(copyContent).then(() => {
        showToast('已复制到剪贴板');
    }).catch(() => {
        showToast('复制失败', 'danger');
    });
}

async function deleteResource(id) {
    if (await showConfirm('确定要删除这条资源吗？此操作不可恢复。', 'danger')) {
        try {
            const response = await fetch(`/api/resources/${id}`, { method: 'DELETE' });
            const data = await response.json();

            if (data.success) {
                showToast('删除成功');
                loadResources();
            } else {
                showToast(data.message || '删除失败', 'danger');
            }
        } catch (error) {
            showToast('删除请求失败', 'danger');
        }
    }
}

async function editResource(id) {
    try {
        const response = await fetch(`/api/resources/${id}`);
        const data = await response.json();

        if (data.success) {
            const res = data.data;
            document.getElementById('editResourceId').value = res.id;
            document.getElementById('editResourceName').value = res.name;
            document.getElementById('editResourceShareLink').value = res.share_link;
            document.getElementById('editResourceCloudName').value = res.cloud_name || '';
            document.getElementById('editResourceType').value = res.type || '';
            document.getElementById('editResourceRemarks').value = res.remarks || '';

            new bootstrap.Modal(document.getElementById('editResourceModal')).show();
        } else {
            showToast(data.message, 'danger');
        }
    } catch (error) {
        showToast('获取详情失败', 'danger');
    }
}

// ==========================================
// 6. 核心业务逻辑
// ==========================================

async function saveResource() {
    if (!addResourceForm.checkValidity()) {
        addResourceForm.reportValidity();
        return;
    }

    const shareLink = document.getElementById('resourceShareLink').value.trim();
    const cloudName = matchNetdiskLink(shareLink);

    const saveToNetdisk = {
        quark: document.getElementById('resourceSaveToQuark').checked,
        baidu: document.getElementById('resourceSaveToBaidu').checked,
        ali: document.getElementById('resourceSaveToAli').checked,
        xunlei: document.getElementById('resourceSaveToXunlei').checked,
        uc: document.getElementById('resourceSaveToUc').checked,
        wukong: document.getElementById('resourceSaveToWukong').checked,
    };

    const payload = {
        name: document.getElementById('resourceName').value.trim(),
        share_link: shareLink,
        cloud_name: cloudName,
        type: document.getElementById('resourceType').value,
        remarks: document.getElementById('resourceRemarks').value.trim(),
        save_to_netdisk: saveToNetdisk
    };

    saveResourceBtn.disabled = true;
    saveResourceBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 保存中...';

    try {
        const response = await fetch('/api/resources', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (data.success) {
            showToast('资源添加成功');
            bootstrap.Modal.getInstance(document.getElementById('addResourceModal')).hide();
            addResourceForm.reset();
            loadResources();
        } else {
            showToast(data.message || '添加失败', 'danger');
        }
    } catch (error) {
        console.error(error);
        showToast('请求失败，请检查网络', 'danger');
    } finally {
        saveResourceBtn.disabled = false;
        saveResourceBtn.innerHTML = '<i class="fas fa-save"></i> 保存';
    }
}

async function updateResource() {
    if (!editResourceForm.checkValidity()) {
        editResourceForm.reportValidity();
        return;
    }

    const id = document.getElementById('editResourceId').value;
    const shareLink = document.getElementById('editResourceShareLink').value.trim();
    const cloudName = matchNetdiskLink(shareLink);

    const payload = {
        name: document.getElementById('editResourceName').value.trim(),
        share_link: shareLink,
        cloud_name: cloudName,
        type: document.getElementById('editResourceType').value,
        remarks: document.getElementById('editResourceRemarks').value.trim()
    };

    updateResourceBtn.disabled = true;
    updateResourceBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 更新中...';

    try {
        const response = await fetch(`/api/resources/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (data.success) {
            showToast('更新成功');
            bootstrap.Modal.getInstance(document.getElementById('editResourceModal')).hide();
            loadResources();
        } else {
            showToast(data.message || '更新失败', 'danger');
        }
    } catch (error) {
        showToast('更新请求异常', 'danger');
    } finally {
        updateResourceBtn.disabled = false;
        updateResourceBtn.innerHTML = '<i class="fas fa-save"></i> 保存修改';
    }
}

function parseBatchResources(content) {
    const resources = [];
    const lines = content.split('\n');
    let currentResource = {};

    lines.forEach(line => {
        line = line.trim();
        if (!line) return;

        const titleMatch = line.match(/^(?:标题|name)[:：]\s*(.+)$/i);
        if (titleMatch) {
            if (currentResource.name && currentResource.share_link) {
                resources.push(currentResource);
                currentResource = {};
            }
            currentResource.name = titleMatch[1].trim();
            return;
        }

        const linkMatch = line.match(/^(?:链接|分享链接|share_link)[:：]\s*(.+)$/i);
        if (linkMatch) {
            currentResource.share_link = linkMatch[1].trim();
            if (!currentResource.cloud_name) {
                currentResource.cloud_name = matchNetdiskLink(currentResource.share_link);
            }
            return;
        }

        const typeMatch = line.match(/^(?:类型|type)[:：]\s*(.+)$/i);
        if (typeMatch) {
            currentResource.type = typeMatch[1].trim();
            return;
        }
        
        const remarkMatch = line.match(/^(?:备注|remark|remarks)[:：]\s*(.+)$/i);
        if (remarkMatch) {
            currentResource.remarks = remarkMatch[1].trim();
            return;
        }
    });

    if (currentResource.name && currentResource.share_link) {
        resources.push(currentResource);
    }

    return resources;
}

async function batchSaveResources() {
    const content = document.getElementById('batchResourceContent').value.trim();
    if (!content) {
        showToast('请输入内容', 'warning');
        return;
    }

    const resources = parseBatchResources(content);
    if (resources.length === 0) {
        showToast('未能解析出有效资源，请检查格式', 'danger');
        return;
    }

    if (resources.length > 10) {
        showToast('单次添加建议不超过10条', 'warning');
        return;
    }

    const commonType = document.getElementById('batchResourceType').value;
    const commonRemarks = document.getElementById('batchResourceRemarks').value.trim();

    const saveToNetdisk = {
        quark: document.getElementById('resourceSaveToQuark').checked,
        baidu: document.getElementById('resourceSaveToBaidu').checked,
        ali: document.getElementById('resourceSaveToAli').checked,
        xunlei: document.getElementById('resourceSaveToXunlei').checked,
        uc: document.getElementById('resourceSaveToUc').checked,
        wukong: document.getElementById('resourceSaveToWukong').checked,
    };

    batchSaveResourceBtn.disabled = true;
    let successCount = 0;

    try {
        for (let i = 0; i < resources.length; i++) {
            const res = resources[i];
            batchSaveResourceBtn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> 正在保存 ${i + 1}/${resources.length}`;

            const payload = {
                name: res.name,
                share_link: res.share_link,
                cloud_name: res.cloud_name || matchNetdiskLink(res.share_link),
                type: res.type || commonType,
                remarks: res.remarks || commonRemarks,
                save_to_netdisk: saveToNetdisk
            };

            const response = await fetch('/api/resources', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (data.success) successCount++;
        }

        showToast(`批量处理完成：成功 ${successCount}，失败 ${resources.length - successCount}`, 'success');
        
        bootstrap.Modal.getInstance(document.getElementById('batchAddResourceModal')).hide();
        batchAddResourceForm.reset();
        loadResources();

    } catch (error) {
        console.error(error);
        showToast('批量处理过程中断', 'danger');
    } finally {
        batchSaveResourceBtn.disabled = false;
        batchSaveResourceBtn.innerHTML = '<i class="fas fa-save"></i> 批量添加';
    }
}

async function loadCookieConfig() {
    try {
        const response = await fetch('/cookie-config');
        const data = await response.json();
        if (baiduCookieInput) baiduCookieInput.value = data.baidu_cookie || '';
        if (quarkCookieInput) quarkCookieInput.value = data.quark_cookie || '';
    } catch (error) {
        console.error('加载Cookie失败:', error);
    }
}

async function saveCookieConfig() {
    const payload = {
        baidu_cookie: baiduCookieInput.value.trim(),
        quark_cookie: quarkCookieInput.value.trim()
    };

    try {
        const response = await fetch('/cookie-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (data.success) {
            showToast('Cookie配置保存成功', 'success');
            const modalInstance = bootstrap.Modal.getInstance(cookieConfigModal);
            if (modalInstance) modalInstance.hide();
        } else {
            showToast('保存失败: ' + data.message, 'danger');
        }
    } catch (error) {
        showToast('请求失败，请检查网络', 'danger');
    }
}

async function uploadQrCode() {
    const fileInput = document.getElementById('qrCodeFile');
    if (!fileInput) {
        showToast('找不到文件输入元素', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    if (!file) {
        showToast('请选择二维码图片', 'danger');
        return;
    }
    
    const formData = new FormData();
    formData.append('qr_code', file);
    
    try {
        const response = await fetch('/upload-qr-code', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if (data.success) {
            showToast('二维码上传成功', 'success');
            const currentQrCodeImg = document.getElementById('qrConfigImage');
            if (currentQrCodeImg) {
                currentQrCodeImg.src = '/get-qr-code?' + new Date().getTime();
            }
            fileInput.value = '';
            const previewDiv = document.getElementById('qrCodePreview');
            if (previewDiv) {
                previewDiv.innerHTML = '<small class="text-muted">选择文件后预览</small>';
            }
            const modalElement = document.getElementById('qrCodeConfigModal');
            const modalInstance = bootstrap.Modal.getInstance(modalElement);
            if (modalInstance) modalInstance.hide();
        } else {
            showToast('上传失败: ' + data.message, 'danger');
        }
    } catch (error) {
        console.error('上传二维码失败:', error);
        showToast('请求失败，请检查网络', 'danger');
    }
}

async function loadQuotaInfo() {
    const quotaCard = document.getElementById('quotaInfoCard');
    const quotaTotal = document.getElementById('quotaTotal');
    const quotaUsed = document.getElementById('quotaUsed');
    const quotaFree = document.getElementById('quotaFree');
    const quotaPercent = document.getElementById('quotaPercent');
    const progressBar = document.getElementById('quotaProgressBar');
    
    try {
        const response = await fetch('/api/quota');
        const data = await response.json();
        
        if (data.success) {
            const quota = data.data;
            quotaTotal.textContent = quota.total_gb + ' GB';
            quotaUsed.textContent = quota.used_gb + ' GB';
            quotaFree.textContent = quota.free_gb + ' GB';
            quotaPercent.textContent = quota.used_percent + '%';
            
            progressBar.style.width = quota.used_percent + '%';
            progressBar.textContent = quota.used_percent + '%';
            
            if (quota.used_percent >= 90) {
                progressBar.className = 'progress-bar bg-danger';
                quotaPercent.className = 'h5 text-danger';
            } else if (quota.used_percent >= 80) {
                progressBar.className = 'progress-bar bg-warning';
                quotaPercent.className = 'h5 text-warning';
            } else {
                progressBar.className = 'progress-bar bg-success';
                quotaPercent.className = 'h5 text-success';
            }
            
            quotaCard.classList.remove('d-none');
            showToast('空间信息加载成功', 'success');
        } else {
            showToast('获取空间信息失败: ' + data.message, 'danger');
        }
    } catch (error) {
        console.error('加载空间信息失败:', error);
        showToast('请求失败，请检查网络', 'danger');
    }
}

async function cleanOldFiles() {
    if (!confirm('确定要清理旧文件吗？这将删除网盘中最旧的文件以释放空间。')) {
        return;
    }
    
    const cleanBtn = document.getElementById('cleanFilesBtn');
    const originalText = cleanBtn.innerHTML;
    cleanBtn.disabled = true;
    cleanBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 清理中...';
    
    try {
        const response = await fetch('/api/clean', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ threshold: 80, count: 20 })
        });
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            loadQuotaInfo();
        } else {
            showToast('清理失败: ' + data.message, 'danger');
        }
    } catch (error) {
        console.error('清理文件失败:', error);
        showToast('请求失败，请检查网络', 'danger');
    } finally {
        cleanBtn.disabled = false;
        cleanBtn.innerHTML = originalText;
    }
}

// ==========================================
// 7. 初始化入口
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    const qrConfigImg = document.getElementById('qrConfigImage');
    if (qrConfigImg) {
        qrConfigImg.src = '/get-qr-code';
    }
    
    loadResources();

    if (pagination) {
        pagination.addEventListener('click', (e) => {
            e.preventDefault();
            const target = e.target.closest('a');
            if (target) {
                const page = parseInt(target.getAttribute('data-page'));
                if (!isNaN(page) && page >= 1 && page <= totalPages && page !== currentPage) {
                    currentPage = page;
                    loadResources();
                }
            }
        });
    }

    if (searchInput) {
        let timeout = null;
        searchInput.addEventListener('input', () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                currentPage = 1;
                loadResources();
            }, 300);
        });
    }

    if (cookieConfigModal) {
        cookieConfigModal.addEventListener('show.bs.modal', loadCookieConfig);
    }

    if (saveCookieConfigBtn) {
        saveCookieConfigBtn.addEventListener('click', saveCookieConfig);
    }

    const qrCodeConfigModal = document.getElementById('qrCodeConfigModal');
    if (qrCodeConfigModal) {
        qrCodeConfigModal.addEventListener('show.bs.modal', () => {
            const qrConfigImg = document.getElementById('qrConfigImage');
            if (qrConfigImg) {
                qrConfigImg.src = '/get-qr-code?' + new Date().getTime();
            }
            const previewDiv = document.getElementById('qrCodePreview');
            if (previewDiv) {
                previewDiv.innerHTML = '<small class="text-muted">选择文件后预览</small>';
            }
            const fileInput = document.getElementById('qrCodeFile');
            if (fileInput) {
                fileInput.value = '';
            }
        });
    }
    
    const uploadQrCodeBtn = document.getElementById('uploadQrCodeBtn');
    if (uploadQrCodeBtn) {
        uploadQrCodeBtn.addEventListener('click', uploadQrCode);
    }

    if (saveResourceBtn) {
        saveResourceBtn.addEventListener('click', saveResource);
    }
    
    if (updateResourceBtn) {
        updateResourceBtn.addEventListener('click', updateResource);
    }
    
    if (batchSaveResourceBtn) {
        batchSaveResourceBtn.addEventListener('click', batchSaveResources);
    }

    // 采集电影数据相关
    const startCrawlBtn = document.getElementById('startCrawlBtn');
    if (startCrawlBtn) {
        startCrawlBtn.addEventListener('click', startCrawlMovies);
    }
});

// 开始采集电影数据
async function startCrawlMovies() {
    const category = document.getElementById('crawlCategory').value;
    const pages = parseInt(document.getElementById('crawlPages').value);
    
    const startCrawlBtn = document.getElementById('startCrawlBtn');
    const crawlProgress = document.getElementById('crawlProgress');
    const crawlStatus = document.getElementById('crawlStatus');
    const crawlProgressBar = document.getElementById('crawlProgressBar');
    const crawlResult = document.getElementById('crawlResult');
    const crawlResultText = document.getElementById('crawlResultText');
    
    // 显示进度条
    if (crawlProgress) {
        crawlProgress.classList.remove('d-none');
    }
    if (crawlResult) {
        crawlResult.classList.add('d-none');
    }
    
    // 禁用按钮
    if (startCrawlBtn) {
        startCrawlBtn.disabled = true;
        startCrawlBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 采集ing...';
    }
    
    try {
        let response, data;
        
        // 根据分类选择不同的API端点
        if (category === '热门榜') {
            response = await fetch(`/api/movies/crawl/hot`);
        } else if (category === '新上映') {
            response = await fetch(`/api/movies/crawl/new`);
        } else {
            response = await fetch(`/api/movies/crawl?category=${encodeURIComponent(category)}&pages=${pages}`);
        }
        
        data = await response.json();
        
        if (data.code === 0) {
            // 隐藏加载状态，显示成功结果
            if (crawlProgress) {
                crawlProgress.classList.add('d-none');
            }
            if (crawlResult) {
                crawlResult.classList.remove('d-none');
            }
            if (crawlResultText) {
                const count = data.data?.count || data.data?.saved_count || 0;
                crawlResultText.textContent = `采集完成，共保存 ${count} 条 ${category} 数据`;
            }
            const count = data.data?.count || data.data?.saved_count || 0;
            showToast(`采集 ${category} 数据成功，共保存 ${count} 条`, 'success');
        } else {
            // 隐藏加载状态，显示失败结果
            if (crawlProgress) {
                crawlProgress.classList.add('d-none');
            }
            showToast(`采集失败: ${data.message}`, 'danger');
        }
    } catch (error) {
        // 隐藏加载状态，显示错误结果
        if (crawlProgress) {
            crawlProgress.classList.add('d-none');
        }
        console.error('采集电影数据失败:', error);
        showToast('采集请求失败，请检查网络', 'danger');
    } finally {
        // 恢复按钮状态
        if (startCrawlBtn) {
            startCrawlBtn.disabled = false;
            startCrawlBtn.innerHTML = '开始采集';
        }
    }
}
