// --- HTML 转义函数，防止 XSS 攻击 ---
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// --- 全局状态管理和 DOM 元素 ---
let allResults = [];
let isSearchRunning = false;
let currentPage = 1;
const itemsPerPage = 20;
let isLoadingNextBatch = false;
let isFullyLoaded = false;
let currentFilter = '全部';

// DOM 元素引用
let filterBar, scrollableResultsDiv, searchButton, searchInput, resultContainer, loadingMore, resultCountText, statusBar;

// 页面加载时检查 URL 是否包含 keyword 参数
function checkUrlForKeyword() {
    // 初始化 DOM 元素引用
    filterBar = document.getElementById('netdisk-filter-bar');
    scrollableResultsDiv = document.getElementById('scrollableResults');
    searchButton = document.getElementById('searchButton');
    searchInput = document.getElementById('searchInput');
    resultContainer = document.getElementById('resultContainer');
    loadingMore = document.getElementById('loadingMore');
    resultCountText = document.getElementById('resultCountText');
    statusBar = document.getElementById('statusBar');
    
    // 绑定搜索按钮事件
    if (searchButton) {
        searchButton.addEventListener('click', performSearch);
    }
    
    // 绑定搜索输入框回车事件
    if (searchInput) {
        searchInput.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                performSearch();
            }
        });
        
        // 添加搜索栏展开/收起动画
        const inputGroup = document.querySelector('.input-group-custom');
        if (inputGroup) {
            searchInput.addEventListener('focus', function() {
                inputGroup.classList.add('expanded');
            });
            
            searchInput.addEventListener('blur', function() {
                if (this.value.trim() === '') {
                    inputGroup.classList.remove('expanded');
                }
            });
        }
    }
    
    // 绑定网盘过滤事件
    if (filterBar) {
        filterBar.addEventListener('click', (event) => {
            const button = event.target.closest('.filter-btn');
            if (button) {
                const netdisk = button.getAttribute('data-netdisk');
                if (netdisk === currentFilter) return;
                currentFilter = netdisk;
                filterBar.querySelectorAll('.filter-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                button.classList.add('active');
                renderResults(true);
                if (scrollableResultsDiv) {
                    scrollableResultsDiv.scrollTop = 0;
                }
            }
        });
    }
    
    // 检查 URL 参数
    const urlParams = new URLSearchParams(window.location.search);
    const keyword = urlParams.get('keyword');
    if (keyword && searchInput) {
        searchInput.value = keyword;
    }
}

// 页面加载完成后检查 URL 参数
document.addEventListener('DOMContentLoaded', function() {
    // 先初始化DOM元素
    checkUrlForKeyword();
    
    // 然后延迟执行搜索，确保页面完全渲染
    const urlParams = new URLSearchParams(window.location.search);
    const keyword = urlParams.get('keyword');
    if (keyword) {
        setTimeout(function() {
            if (searchInput) {
                searchInput.value = keyword;
                performSearch();
            }
        }, 1000);
    }
});


// --- 辅助函数：网盘颜色区分 (保持不变) ---
function getNetdiskColorClass(netdiskName) {
    let badgeClass = 'bg-secondary';
    let badgeTextClass = 'text-white';

    if (netdiskName.includes('百度网盘')) badgeClass = 'bg-mid-blue';
    else if (netdiskName.includes('夸克网盘')) badgeClass = 'bg-terracotta';
    else if (netdiskName.includes('悟空网盘')) badgeClass = 'bg-navy-blue';
    else if (netdiskName.includes('快兔网盘')) badgeClass = 'bg-coral';
    else if (netdiskName.includes('115网盘')) badgeClass = 'bg-orange';
    else if (netdiskName.includes('迅雷网盘')) badgeClass = 'bg-teal';
    else if (netdiskName.includes('UC网盘')) badgeClass = 'bg-warm-gold';
    else if (netdiskName.includes('移动云盘')) badgeClass = 'bg-light-green';
    else if (netdiskName.includes('天翼云盘')) badgeClass = 'bg-deep-violet';
    else if (netdiskName.includes('123云盘')) badgeClass = 'bg-purple';
    else if (netdiskName.includes('阿里云盘')) badgeClass = 'bg-dark-mint';
    else if (netdiskName.includes('联通云盘')) badgeClass = 'bg-olive';
        else if (netdiskName.includes('PikPak')) badgeClass = 'bg-salmon';
    else if (netdiskName.includes('磁力链接') || netdiskName.includes('迅雷链接') || netdiskName.includes('电驴链接')) badgeClass = 'bg-dark';

    if (badgeClass !== 'bg-warning') {
        badgeTextClass = 'text-white';
    }

    return { badgeClass, badgeTextClass };
}

// 前端去重辅助函数 (保持不变)
function filterUnique2ndDomainFront(lst) {
    const seenCombinations = new Set();
    const result = [];
    for (const subList of lst) {
        if (subList.length >= 4) {
            const title = subList[1];
            const url = subList[2];
            try {
                let domain = '';
                if (url.startsWith('http://') || url.startsWith('https://')) {
                    const urlObj = new URL(url);
                    domain = urlObj.hostname;
                } else {
                    domain = url;
                }
                const combination = `${title}|${domain}`;
                if (!seenCombinations.has(combination)) {
                    seenCombinations.add(combination);
                    result.push(subList);
                }
            } catch (e) {
                const combination = `${title}|${url}`;
                if (!seenCombinations.has(combination)) {
                    seenCombinations.add(combination);
                    result.push(subList);
                }
            }
        }
    }
    return result;
}

// --- 搜索和结果管理 ---

/**
 * 动态创建网盘过滤按钮。
 */
function updateFilterButtons() {
    if (!filterBar) return;
    
    const validResults = allResults.filter(item => item[5] !== false);
    const invalidResults = allResults.filter(item => item[5] === false);
    const netdiskNames = new Set(validResults.map(item => item[3]));
    
    // 移除所有除了"全部"的按钮
    const buttonsToRemove = Array.from(filterBar.querySelectorAll('.filter-btn, .invalid-btn'))
        .filter(btn => btn.getAttribute('data-netdisk') !== '全部');
    buttonsToRemove.forEach(btn => btn.remove());

    if (validResults.length > 0 || invalidResults.length > 0) {
        filterBar.classList.remove('d-none');
        if (resultCountText) {
            resultCountText.classList.add('d-none');
        }
    } else {
         filterBar.classList.add('d-none');
    }

    const countByNetdisk = {};
    validResults.forEach(item => {
        const netdisk = item[3];
        countByNetdisk[netdisk] = (countByNetdisk[netdisk] || 0) + 1;
    });
    countByNetdisk['全部'] = validResults.length;

    const dynamicNames = Array.from(netdiskNames).filter(name => name !== '全部' && name !== '其他');

    dynamicNames.forEach(name => {
        const button = document.createElement('button');
        button.className = 'filter-btn';
        button.innerHTML = `${name} (${countByNetdisk[name] || 0})`;
        button.setAttribute('data-netdisk', name);

        if (name === currentFilter) {
            button.classList.add('active');
        }
        filterBar.appendChild(button);
    });

    const hasOther = netdiskNames.has('其他');
    if (hasOther) {
        const otherButton = document.createElement('button');
        otherButton.className = 'filter-btn';
        otherButton.innerHTML = `其他 (${countByNetdisk['其他'] || 0})`;
        otherButton.setAttribute('data-netdisk', '其他');

        if ('其他' === currentFilter) {
            otherButton.classList.add('active');
        }
        filterBar.appendChild(otherButton);
    }

    const allButton = filterBar.querySelector('[data-netdisk="全部"]');
    if (allButton) {
        allButton.innerHTML = `全部 (${countByNetdisk['全部'] || 0})`;
        if (currentFilter === '全部') {
            allButton.classList.add('active');
        } else {
            allButton.classList.remove('active');
        }
    }
    
    // 添加无效链接按钮
    if (invalidResults.length > 0) {
        const invalidButton = document.createElement('button');
        invalidButton.className = 'filter-btn invalid-btn';
        invalidButton.innerHTML = `无效 (${invalidResults.length})`;
        invalidButton.setAttribute('data-netdisk', '无效');
        invalidButton.style.cssText = 'opacity: 0.6; cursor: not-allowed; background-color: #f5f5f5;';
        invalidButton.disabled = true;
        filterBar.appendChild(invalidButton);
    }

    document.querySelectorAll('.filter-btn:not(.invalid-btn)').forEach(button => {
        button.onclick = function() {
            currentFilter = this.getAttribute('data-netdisk');
            renderResults(true);
            updateFilterButtons();
        };
    });
}

/**
 * 执行流式搜索（SSE）
 */
function performSearch() {
    if (isSearchRunning) return;
    if (!searchInput || !searchButton || !statusBar || !resultCountText || !loadingMore || !filterBar || !resultContainer || !scrollableResultsDiv) return;

    const keyword = searchInput.value;
    if (!keyword) {
        alert('请输入搜索关键词');
        return;
    }

    isSearchRunning = true;
    isFullyLoaded = false;
    searchButton.disabled = true;

    searchButton.classList.add('is-flying');
    searchButton.classList.add('searching');

    statusBar.classList.remove('d-none');
    statusBar.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> 正在持续搜索更多资源...';

    resultCountText.classList.add('d-none');
    loadingMore.classList.add('d-none');

    allResults = [];
    currentPage = 1;
    currentFilter = '全部';
    filterBar.classList.add('d-none');

    resultContainer.innerHTML = '<p class="text-center text-muted p-4">正在连接并等待结果流...</p>';
    scrollableResultsDiv.removeEventListener('scroll', infiniteScrollHandler);
    
    const doubanSection = document.getElementById('doubanHotSection');
    const filterCountContainer = document.querySelector('.filter-and-count-container');
    const heroSection = document.querySelector('.hero-row');
    if (doubanSection) {
        doubanSection.style.opacity = '0';
        doubanSection.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            doubanSection.style.display = 'none';
        }, 600);
    }
    if (heroSection) {
        heroSection.style.opacity = '0';
        heroSection.style.transform = 'translateY(-20px)';
        heroSection.style.maxHeight = '0';
        setTimeout(() => {
            heroSection.style.display = 'none';
        }, 600);
    }
    if (filterCountContainer) filterCountContainer.classList.remove('d-none');
    if (resultContainer) resultContainer.classList.remove('d-none');

    const eventSource = new EventSource(`/api/search_stream?keyword=${encodeURIComponent(keyword)}`);

    const searchTimeout = setTimeout(function() {
        if (eventSource) {
            eventSource.close();
            finalizeSearch();
            showToast('搜索超时，请重试', 'warning');
        }
    }, 30000);

    // 首批结果到达后，设置提前结束定时器
    let _firstResultsArrived = false;
    let _earlyFinishTimer = null;
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);

            if (data.type === 'end') {
                clearTimeout(searchTimeout);
                if (_earlyFinishTimer) clearTimeout(_earlyFinishTimer);
                eventSource.close();
                finalizeSearch();
            } else if (data.results && data.results.length > 0) {
                const currentLength = allResults.length;
                allResults.push(...data.results);
                allResults = filterUnique2ndDomainFront(allResults);

                if (allResults.length > currentLength) {
                    updateFilterButtons();
                    // 首批结果到达时立即渲染卡片
                    renderResults(currentLength === 0);
                    
                    // 首批结果到达后，设置 3 秒自动结束（不等慢 API）
                    if (!_firstResultsArrived) {
                        _firstResultsArrived = true;
                        _earlyFinishTimer = setTimeout(function() {
                            if (isSearchRunning) {
                                console.log('已有结果，提前结束搜索等待');
                                clearTimeout(searchTimeout);
                                eventSource.close();
                                finalizeSearch();
                            }
                        }, 3000);
                    }
                }
            }
        } catch (error) {
            console.error('解析流数据出错:', error);
            console.error('出错的事件数据:', event.data);
        }
    };

    eventSource.onerror = function(error) {
        console.error('EventSource 错误:', error);
        clearTimeout(searchTimeout);
        eventSource.close();
        resultContainer.innerHTML = '<p class="text-center text-danger p-4">搜索连接出错或服务器异常。</p>';
        finalizeSearch(true);
    };
}

/**
 * 搜索完成或出错时的清理工作
 */
function finalizeSearch(hasError = false) {
    isSearchRunning = false;
    searchButton.disabled = false;

    searchButton.classList.remove('is-flying');
    searchButton.classList.remove('searching');

    statusBar.classList.add('d-none');

    if (allResults.length === 0 && !hasError) {
        resultContainer.innerHTML = `
            <div class="text-center initial-prompt-area">
                <div class="initial-icon-wrapper">
                    <i class="fas fa-cloud-upload-alt"></i>
                </div>
                <h3 class="mt-3 text-muted">未找到相关结果，请尝试其他关键词</h3>
            </div>`;
        loadingMore.classList.add('d-none');
        document.querySelector('.filter-and-count-container').classList.remove('d-none');
        resultCountText.classList.add('d-none');
    } else if (!hasError) {
        updateFilterButtons();
        document.querySelector('.filter-and-count-container').classList.remove('d-none');
        renderResults(true);
        scrollableResultsDiv.addEventListener('scroll', infiniteScrollHandler);
        startValidityCheck();
    }
}

/**
 * 渲染搜索结果到页面
 */
function renderResults(reset = false) {
    if (!resultContainer) return;
    
    let filteredResults = allResults.filter(result => {
        const matchesNetdisk = currentFilter === '全部' || result[3] === currentFilter;
        const isNotInvalid = result[5] !== false;
        return matchesNetdisk && isNotInvalid;
    });

    if (reset) {
        currentPage = 1;
        resultContainer.innerHTML = '';
    }

    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const currentBatch = filteredResults.slice(startIndex, endIndex);

    if (resultCountText) {
        resultCountText.classList.add('d-none');
    }
    
    if (filteredResults.length > 0) {
        resultContainer.querySelector('p.text-center.text-muted')?.remove();
    } else if (!isSearchRunning && reset) {
        resultContainer.innerHTML = `<div class="text-center p-5"><p class="text-muted">在 ${currentFilter} 中未找到相关结果</p></div>`;
    }

    if (currentBatch.length > 0) {
        const fragment = document.createDocumentFragment();
        
        currentBatch.forEach((result, index) => {
            const source = result[0];
            const titleText = result[1];
            const urlLink = result[2];
            const netdiskName = result[3];
            const datetimeStr = result[4] || '';
            const is_valid = result[5];
            // 直接找到这个 result 在 allResults 中的原始索引
            let originalIndex = -1;
            for (let i = 0; i < allResults.length; i++) {
                if (allResults[i] === result) {
                    originalIndex = i;
                    break;
                }
            }

            const { badgeClass, badgeTextClass } = getNetdiskColorClass(netdiskName);
            const hotClass = source === 'hot' ? 'hot-result' : '';

            const finalBadgeClass = `${badgeClass} ${badgeTextClass}`;
            
            let validityBadgeHtml = '';
            if (is_valid === true || is_valid === false) {
                const validityClass = is_valid ? 'valid-link' : 'invalid-link';
                const validityText = is_valid ? '有效' : '无效';
                validityBadgeHtml = `<span class="validity-badge ${validityClass}">${validityText}</span>`;
            }

            const fullItem = document.createElement('div');

            const itemHtml = `
                <div class="result-item ${hotClass}">
                    <div class="result-title">${escapeHtml(titleText)}</div>
                    <div class="result-meta">
                        <span class="result-datetime">${escapeHtml(datetimeStr) || ''}</span>
                        <div class="result-actions">
                            <span class="netdisk-badge ${finalBadgeClass}">${escapeHtml(netdiskName)}</span>
                            ${validityBadgeHtml}
                            <button class="btn btn-sm open-button btn-outline-primary" data-title="${escapeHtml(titleText)}" data-url="${escapeHtml(urlLink)}" data-netdisk="${escapeHtml(netdiskName)}">
                                <i class="fas fa-external-link-alt"></i> 打开
                            </button>
                        </div>
                    </div>
                </div>
                ${(startIndex + index) < filteredResults.length - 1 ? '<hr class="result-divider">' : ''}
            `;
            fullItem.innerHTML = itemHtml;
            fragment.appendChild(fullItem);
            
            const resultItem = fullItem.querySelector('.result-item');
            if (resultItem && originalIndex >= 0) {
                resultItem.dataset.resultIndex = originalIndex;
            }
        });
        
        resultContainer.appendChild(fragment);
        
        const openButtons = resultContainer.querySelectorAll('.open-button:not([data-click-handler])');
        openButtons.forEach(button => {
            button.setAttribute('data-click-handler', 'true');
            button._clickHandler = function() {
                openAndWash(this);
            };
            button.addEventListener('click', button._clickHandler);
        });
    }

    if (endIndex >= filteredResults.length) {
        isFullyLoaded = true;
        loadingMore.classList.add('d-none');
        loadingMore.textContent = '已加载全部结果。';
    } else {
        isFullyLoaded = false;
        loadingMore.classList.remove('d-none');
        loadingMore.innerHTML = '<div class="spinner-border spinner-border-sm me-2" role="status"><span class="visually-hidden">Loading...</span></div>加载更多结果...';
    }

    if (currentBatch.length > 0) {
        currentPage++;
    }
    isLoadingNextBatch = false;
    
    updateValidityStatus();
}

/**
 * 更新所有结果的有效性状态
 */
function updateValidityStatus() {
    const resultElements = resultContainer.querySelectorAll('.result-item');
    
    resultElements.forEach(resultElement => {
        const resultIndex = parseInt(resultElement.dataset.resultIndex);
        if (isNaN(resultIndex) || resultIndex < 0 || resultIndex >= allResults.length) {
            return;
        }
        
        const result = allResults[resultIndex];
        const validityBadge = resultElement.querySelector('.validity-badge');
        const openButton = resultElement.querySelector('.open-button');
        
        if (result[5] === true || result[5] === false) {
            // 链接无效时隐藏结果项
            if (result[5] === false) {
                resultElement.style.display = 'none';
                const divider = resultElement.nextElementSibling;
                if (divider && divider.classList.contains('result-divider')) {
                    divider.style.display = 'none';
                }
                return;
            }
            
            // 链接有效时显示结果项
            resultElement.style.display = 'block';
            const divider = resultElement.nextElementSibling;
            if (divider && divider.classList.contains('result-divider')) {
                divider.style.display = 'block';
            }
            
            const validityClass = result[5] ? 'valid-link' : 'invalid-link';
            const validityText = result[5] ? '有效' : '无效';
            
            if (validityBadge) {
                const currentValidityText = validityBadge.textContent.trim();
                if (currentValidityText !== validityText) {
                    validityBadge.className = `validity-badge ${validityClass}`;
                    validityBadge.textContent = validityText;
                }
            } else {
                const resultActions = resultElement.querySelector('.result-actions');
                if (resultActions) {
                    const netdiskBadge = resultActions.querySelector('.netdisk-badge');
                    if (netdiskBadge) {
                        const newValidityBadge = document.createElement('span');
                        newValidityBadge.className = `validity-badge ${validityClass}`;
                        newValidityBadge.textContent = validityText;
                        netdiskBadge.after(newValidityBadge);
                    }
                }
            }
            
            // 更新打开按钮状态
            if (openButton) {
                if (result[5] === false) {
                    // 链接无效，禁用按钮
                    openButton.disabled = true;
                    openButton.classList.add('btn-outline-secondary');
                    openButton.classList.remove('btn-outline-primary');
                } else {
                    // 链接有效，启用按钮
                    openButton.disabled = false;
                    openButton.classList.add('btn-outline-primary');
                    openButton.classList.remove('btn-outline-secondary');
                }
            }
        } else {
            if (validityBadge) {
                validityBadge.remove();
            }
            
            // 状态未知时，显示结果项，启用按钮（默认行为）
            resultElement.style.display = 'block';
            const divider = resultElement.nextElementSibling;
            if (divider && divider.classList.contains('result-divider')) {
                divider.style.display = 'block';
            }
            
            if (openButton) {
                openButton.disabled = false;
                openButton.classList.add('btn-outline-primary');
                openButton.classList.remove('btn-outline-secondary');
            }
        }
    });
}

// --- 无限滚动逻辑 ---
const infiniteScrollHandler = () => {
    const container = scrollableResultsDiv;
    if ((container.scrollTop + container.clientHeight) >= (container.scrollHeight - 50) && !isSearchRunning && !isFullyLoaded && !isLoadingNextBatch) {
        loadNextPage();
    }
};

function loadNextPage() {
    isLoadingNextBatch = true;
    loadingMore.classList.remove('d-none');

    setTimeout(() => {
        renderResults(false);
    }, 300);
}


/**
 * 检测是否为移动设备
 */
function isMobileDevice() {
    const userAgent = navigator.userAgent || navigator.vendor || window.opera;
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
    return isMobile;
}

/**
 * 打开并洗白链接
 */
function openAndWash(button) {
    const title = button.getAttribute('data-title');
    const url = button.getAttribute('data-url');
    
    let isCancelled = false;
    let progressInterval = null;
    let currentProgress = 0;
    let controller = new AbortController();
    
    const progressStages = [
        { text: '正在连接资源...', progress: 10, icon: 'fa-link' },
        { text: '正在转存文件...', progress: 40, icon: 'fa-cloud-arrow-down' },
        { text: '正在生成链接...', progress: 75, icon: 'fa-wand-magic-sparkles' },
        { text: '处理完成', progress: 100, icon: 'fa-check' }
    ];
    
    try {
        const originalHtml = button.innerHTML;
        
        // 禁用按钮
        button.disabled = true;
        button.classList.remove('btn-outline-primary');
        button.classList.add('progress-button');
        
        // 创建遮罩层
        const overlay = document.createElement('div');
        overlay.className = 'wash-progress-overlay';
        document.body.appendChild(overlay);
        
        // 创建浮动卡片
        const card = document.createElement('div');
        card.className = 'wash-progress-card';
        
        // 图标
        const iconEl = document.createElement('div');
        iconEl.className = 'wash-card-icon';
        iconEl.innerHTML = '<i class="fas fa-link"></i>';
        
        // 标题
        const titleEl = document.createElement('div');
        titleEl.className = 'wash-card-title';
        titleEl.textContent = title || '资源处理中';
        
        // 状态文字
        const statusEl = document.createElement('div');
        statusEl.className = 'wash-card-status';
        statusEl.textContent = progressStages[0].text;
        
        // 进度条
        const progressTrack = document.createElement('div');
        progressTrack.className = 'wash-card-progress-track';
        const progressFill = document.createElement('div');
        progressFill.className = 'wash-card-progress-fill';
        progressTrack.appendChild(progressFill);
        
        // 步骤指示器
        const stepsEl = document.createElement('div');
        stepsEl.className = 'wash-card-steps';
        progressStages.forEach((_, i) => {
            const dot = document.createElement('div');
            dot.className = 'wash-card-step';
            stepsEl.appendChild(dot);
        });
        
        // 取消按钮
        const cancelButton = document.createElement('button');
        cancelButton.className = 'wash-card-cancel';
        cancelButton.innerHTML = '<i class="fas fa-xmark"></i> 取消操作';
        
        // 组装卡片
        card.appendChild(iconEl);
        card.appendChild(titleEl);
        card.appendChild(statusEl);
        card.appendChild(progressTrack);
        card.appendChild(stepsEl);
        card.appendChild(cancelButton);
        document.body.appendChild(card);
        
        // 关闭卡片函数
        function closeCard() {
            card.classList.add('closing');
            overlay.classList.add('closing');
            setTimeout(() => {
                card.remove();
                overlay.remove();
            }, 260);
        }
        
        // 更新步骤指示器
        function updateSteps(activeIndex) {
            const dots = stepsEl.querySelectorAll('.wash-card-step');
            dots.forEach((dot, i) => {
                dot.classList.remove('active', 'done');
                if (i < activeIndex) dot.classList.add('done');
                else if (i === activeIndex) dot.classList.add('active');
            });
        }
        
        cancelButton.addEventListener('click', (e) => {
            e.stopPropagation();
            isCancelled = true;
            controller.abort();
            
            if (progressInterval) {
                clearInterval(progressInterval);
            }
            
            closeCard();
            
            // 恢复按钮状态
            button.disabled = false;
            button.innerHTML = originalHtml;
            button.classList.remove('progress-button');
            button.classList.add('btn-outline-primary');
            
            showToast('已取消操作', 'info');
        });
        
        // 初始状态
        updateSteps(0);
        progressFill.style.width = progressStages[0].progress + '%';
        
        const startTime = Date.now();
        let currentStageIndex = 0;
        
        // 更新进度显示
        function updateProgress() {
            if (isCancelled) return;
            
            if (currentStageIndex < progressStages.length - 1) {
                currentStageIndex++;
                const stage = progressStages[currentStageIndex];
                statusEl.textContent = stage.text;
                progressFill.style.width = stage.progress + '%';
                iconEl.innerHTML = `<i class="fas ${stage.icon}"></i>`;
                updateSteps(currentStageIndex);
            }
        }
        
        // 每2秒更新一次进度
        progressInterval = setInterval(updateProgress, 2000);
        
        fetch('/api/wash', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                share_url: url,
                title: title
            }),
            signal: controller.signal
        })
        .then(response => response.json())
        .then(data => {
            if (isCancelled) return;
            
            if (progressInterval) {
                clearInterval(progressInterval);
            }
            
            // 显示完成状态
            const isSuccess = data.success || (data.data && data.data.washed_url);
            
            if (isSuccess) {
                iconEl.className = 'wash-card-icon success';
                iconEl.innerHTML = '<i class="fas fa-check"></i>';
                statusEl.textContent = '处理完成，即将跳转...';
                progressFill.className = 'wash-card-progress-fill success';
                progressFill.style.width = '100%';
                updateSteps(progressStages.length);
            } else {
                iconEl.className = 'wash-card-icon error';
                iconEl.innerHTML = '<i class="fas fa-xmark"></i>';
                statusEl.textContent = data.message || '操作失败';
                progressFill.className = 'wash-card-progress-fill error';
                progressFill.style.width = '100%';
            }
            
            // 隐藏取消按钮
            cancelButton.style.display = 'none';
            
            // 短暂延迟后关闭卡片并跳转
            setTimeout(() => {
                if (isCancelled) return;
                
                closeCard();
                
                button.disabled = false;
                button.innerHTML = originalHtml;
                button.classList.remove('progress-button');
                button.classList.add('btn-outline-primary');
                
                if (isSuccess) {
                    const washedUrl = data.data.washed_url;
                    
                    if (!washedUrl) {
                        showToast('未获取到有效链接', 'error');
                        return;
                    }

                    setTimeout(() => {
                        if (isCancelled) return;
                        if (isMobileDevice()) {
                            window.location.href = washedUrl;
                        } else {
                            const newWindow = window.open(washedUrl, '_blank');
                            if (!newWindow) {
                                showToast('弹出窗口被阻止，请允许弹出窗口后重试', 'warning');
                            }
                        }
                    }, 300);
                } else {
                    showToast('操作失败: ' + (data.message || '未知错误'), 'error');
                }
            }, 800);
        })
        .catch(error => {
            if (isCancelled) return;
            
            if (progressInterval) {
                clearInterval(progressInterval);
            }
            
            console.error('洗白请求失败:', error);
            
            iconEl.className = 'wash-card-icon error';
            iconEl.innerHTML = '<i class="fas fa-xmark"></i>';
            statusEl.textContent = '网络错误，请稍后重试';
            progressFill.className = 'wash-card-progress-fill error';
            progressFill.style.width = '100%';
            cancelButton.style.display = 'none';
            
            setTimeout(() => {
                closeCard();
                button.disabled = false;
                button.innerHTML = originalHtml;
                button.classList.remove('progress-button');
                button.classList.add('btn-outline-primary');
                if (error.name !== 'AbortError') {
                    showToast('网络错误，请稍后重试', 'error');
                }
            }, 1000);
        });
    } catch (error) {
        if (progressInterval) {
            clearInterval(progressInterval);
        }
        
        console.error('openAndWash 错误:', error);
        button.disabled = false;
        button.innerHTML = originalHtml;
        button.classList.remove('progress-button');
        button.classList.add('btn-outline-primary');
        showToast('打开链接时发生错误', 'error');
    }
}

/**
 * 单个检查链接的有效性（返回 Promise）
 */
function checkSingleLinkValidity(result, resultIndex) {
    if (result[5] != null) return Promise.resolve();
    
    return fetch('/api/check_validity', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: result[2] })
    })
    .then(response => {
        return response.json();
    })
    .then(data => {
        if (data.success) {
            result[5] = data.data.is_valid;
            
            // 直接用 resultIndex 找对应元素
            const targetElement = document.querySelector(`.result-item[data-result-index="${resultIndex}"]`);
            
            if (targetElement) {
                // 如果链接无效，直接隐藏
                if (data.data.is_valid === false) {
                    targetElement.style.display = 'none';
                    const divider = targetElement.nextElementSibling;
                    if (divider && divider.classList.contains('result-divider')) {
                        divider.style.display = 'none';
                    }
                    return;
                }
                
                // 链接有效时，添加有效标签
                let validityBadge = targetElement.querySelector('.validity-badge');
                const validityClass = 'valid-link';
                const validityText = '有效';
                
                if (validityBadge) {
                    validityBadge.className = `validity-badge ${validityClass}`;
                    validityBadge.textContent = validityText;
                } else {
                    validityBadge = document.createElement('span');
                    validityBadge.className = `validity-badge ${validityClass}`;
                    validityBadge.textContent = validityText;
                    
                    const netdiskBadge = targetElement.querySelector('.netdisk-badge');
                    if (netdiskBadge && netdiskBadge.nextSibling) {
                        targetElement.querySelector('.result-actions').insertBefore(validityBadge, netdiskBadge.nextSibling);
                    } else {
                        targetElement.querySelector('.result-actions').insertBefore(validityBadge, targetElement.querySelector('.open-button'));
                    }
                }
            }
        }
    })
    .catch(error => {
        console.error('检查链接有效性失败:', result[2], error);
    });
}

/**
 * 检查用户可见区域的链接有效性
 */
function checkVisibleLinksValidity() {
    const resultElements = resultContainer.querySelectorAll('.result-item');
    
    resultElements.forEach(element => {
        const rect = element.getBoundingClientRect();
        // 检查元素是否在视口内，加上一定的预加载区域
        if (rect.top >= -200 && rect.bottom <= window.innerHeight + 200) {
            const index = parseInt(element.dataset.resultIndex);
            if (index >= 0 && index < allResults.length && allResults[index][5] == null) {
                // 同时发起所有单个链接的异步检测，不等待
                checkSingleLinkValidity(allResults[index], index);
            }
        }
    });
}

/**
 * 批量检查链接有效性
 */
async function checkLinksValidityBatch(urls) {
    try {
        const response = await fetch('/api/check_validity_batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ urls: urls })
        });
        
        const data = await response.json();
        if (data.success) {
            return data.data;
        }
        return [];
    } catch (error) {
        console.error('批量检查链接有效性失败:', error);
        return [];
    }
}



/**
 * 开始检查链接的有效性（50条一批执行）
 */
async function startValidityCheck() {
    // 增加延迟时间，确保搜索完全完成
    setTimeout(() => {
        console.log('开始异步检查链接有效性...');

        const BATCH_SIZE = 50;
        let currentBatch = 0;

        const processBatch = () => {
            const start = currentBatch * BATCH_SIZE;
            const end = start + BATCH_SIZE;
            const batch = allResults.slice(start, end);

            if (batch.length === 0) {
                console.log('链接有效性检查完成');
                return;
            }

            console.log(`检查第 ${currentBatch + 1} 批链接 (${start + 1}-${end})`);

            const promises = [];
            batch.forEach((result, i) => {
                const index = start + i;
                if (result[5] == null) {
                    promises.push(checkSingleLinkValidity(result, index));
                }
            });

            // 等待这一批完成后，再下一批
            Promise.allSettled(promises).then(() => {
                currentBatch++;
                if (currentBatch * BATCH_SIZE < allResults.length) {
                    setTimeout(processBatch, 100);
                }
            });
        };

        processBatch();
    }, 1000); // 增加延迟到 1 秒
}


