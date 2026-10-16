/**
 * Floating AI chat widget. Works from any page that includes the widget.
 */
(function () {
    'use strict';

    var fab = document.getElementById('ai-chat-fab');
    var panel = document.getElementById('ai-chat-panel');
    var closeBtn = document.getElementById('ai-chat-close');
    var form = document.getElementById('ai-chat-form');
    var input = document.getElementById('ai-chat-input');
    var messages = document.getElementById('ai-chat-messages');
    if (!fab || !panel || !form || !input || !messages) return;

    function csrfToken() {
        var name = 'csrftoken';
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var c = cookies[i].trim();
            if (c.indexOf(name + '=') === 0) {
                return decodeURIComponent(c.substring(name.length + 1));
            }
        }
        var inp = document.querySelector('[name=csrfmiddlewaretoken]');
        return inp ? inp.value : '';
    }

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function linkify(text) {
        // Turn the assistant's " -> /products/..." hints into real links.
        var safe = escapeHtml(text);
        safe = safe.replace(
            /-&gt;\s*(\/[A-Za-z0-9_\-\/\.]+)/g,
            function (_m, url) {
                return ' &rarr; <a href="' + url + '">Open product</a>';
            }
        );
        // Also linkify any bare http(s) URLs.
        safe = safe.replace(
            /(https?:\/\/[^\s)]+)/g,
            '<a href="$1" target="_blank" rel="noopener">link</a>'
        );
        return safe.replace(/\n/g, '<br>');
    }

    function addMessage(text, sender) {
        var div = document.createElement('div');
        div.className = 'ai-chat-message ai-chat-message--' + sender;
        if (sender === 'bot') {
            div.innerHTML = linkify(text);
        } else {
            div.textContent = text;
        }
        messages.appendChild(div);
        scrollToBottom();
    }

    function openPanel() {
        panel.classList.add('is-open');
        input.focus();
    }
    function closePanel() {
        panel.classList.remove('is-open');
    }

    fab.addEventListener('click', openPanel);
    if (closeBtn) closeBtn.addEventListener('click', closePanel);

    async function send(text) {
        addMessage(text, 'user');
        input.value = '';
        try {
            var response = await fetch('/chat/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: 'message=' + encodeURIComponent(text)
            });
            if (!response.ok) throw new Error('Request failed');
            var data = await response.json();
            addMessage(data.message || '…', 'bot');
        } catch (err) {
            addMessage('Sorry, something went wrong. Please try again.', 'bot');
            console.error('Chat widget error:', err);
        }
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        var text = input.value.trim();
        if (text) send(text);
    });

    // Greet once per page load.
    addMessage("Hi! I'm your AI shopping assistant. Ask me anything.", 'bot');
})();
