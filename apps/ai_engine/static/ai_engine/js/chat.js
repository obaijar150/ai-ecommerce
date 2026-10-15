/**
 * AI Chat Assistant — Vanilla JavaScript module.
 */

(function() {
    'use strict';

    const form = document.getElementById('chat-form');
    const input = document.getElementById('chat-input');
    const messagesContainer = document.getElementById('chat-messages');

    if (!form || !input || !messagesContainer) return;

    /**
     * Add a message to the chat window.
     */
    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `chat-message chat-message--${sender}`;
        div.textContent = text;
        messagesContainer.appendChild(div);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    /**
     * Get CSRF token from cookie or hidden input.
     */
    function getCsrfToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                return cookie.substring(name.length + 1);
            }
        }
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    }

    /**
     * Send message to API and display response.
     */
    async function sendMessage(text) {
        try {
            addMessage(text, 'user');
            input.value = '';

            const response = await fetch('/chat/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: `message=${encodeURIComponent(text)}`
            });

            if (!response.ok) throw new Error('Request failed');

            const data = await response.json();
            addMessage(data.message, 'bot');
        } catch (error) {
            addMessage('Sorry, something went wrong. Please try again.', 'bot');
            console.error('Chat error:', error);
        }
    }

    // Handle form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const text = input.value.trim();
        if (text) sendMessage(text);
    });
})();
