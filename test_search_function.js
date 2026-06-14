// 测试搜索功能的脚本
console.log('测试搜索功能');

// 检查是否存在搜索按钮
const searchButton = document.getElementById('searchButton');
const searchInput = document.getElementById('searchInput');

console.log('搜索按钮:', searchButton);
console.log('搜索输入框:', searchInput);

// 检查performSearch函数是否存在
console.log('performSearch函数:', window.performSearch);

// 测试搜索功能
if (searchButton && searchInput && window.performSearch) {
    console.log('所有必要的元素和函数都存在');
    
    // 模拟用户输入
    searchInput.value = '测试';
    console.log('设置搜索关键词为: 测试');
    
    // 模拟点击搜索按钮
    console.log('模拟点击搜索按钮');
    searchButton.click();
    
    console.log('搜索功能测试完成');
} else {
    console.error('缺少必要的元素或函数');
    if (!searchButton) console.error('搜索按钮不存在');
    if (!searchInput) console.error('搜索输入框不存在');
    if (!window.performSearch) console.error('performSearch函数不存在');
}