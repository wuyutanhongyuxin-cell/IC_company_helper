/**
 * WaferCut MES — 全局脚本
 * 确认对话框 + CSRF token 自动注入
 */

(function () {
  'use strict';

  // ====== 危险操作确认对话框 ======
  // 给带 data-confirm="提示文字" 的元素绑定点击确认
  document.addEventListener('click', function (e) {
    var target = e.target.closest('[data-confirm]');
    if (target) {
      var message = target.getAttribute('data-confirm');
      if (!confirm(message)) {
        e.preventDefault();
        e.stopPropagation();
      }
    }
  });

  // ====== CSRF Token 自动注入到 AJAX 请求 ======
  // 从 meta 标签或隐藏字段读取 CSRF token
  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    var input = document.querySelector('input[name="csrf_token"]');
    if (input) return input.value;
    return '';
  }

  // 拦截 fetch 请求，自动加 CSRF header
  var originalFetch = window.fetch;
  window.fetch = function (url, options) {
    options = options || {};
    if (options.method && options.method.toUpperCase() !== 'GET') {
      options.headers = options.headers || {};
      if (!options.headers['X-CSRFToken']) {
        options.headers['X-CSRFToken'] = getCsrfToken();
      }
    }
    return originalFetch.call(this, url, options);
  };
})();
