/**
 * AI E-Commerce Platform — Global JavaScript utilities.
 */

(function() {
    'use strict';

    /**
     * API helper for making fetch requests with CSRF token.
     */
    window.API = {
        get: function(url) {
            return fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            }).then(function(response) {
                if (!response.ok) throw new Error('Request failed: ' + response.status);
                return response.json();
            });
        },

        post: function(url, data) {
            var csrfToken = this.getCsrfToken();
            return fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: JSON.stringify(data)
            }).then(function(response) {
                if (!response.ok) throw new Error('Request failed: ' + response.status);
                return response.json();
            });
        },

        getCsrfToken: function() {
            var name = 'csrftoken';
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.startsWith(name + '=')) {
                    return cookie.substring(name.length + 1);
                }
            }
            // Try to get from hidden input
            var input = document.querySelector('[name=csrfmiddlewaretoken]');
            return input ? input.value : '';
        }
    };

    /**
     * Debounce function for search inputs and scroll handlers.
     */
    window.debounce = function(func, wait) {
        var timeout;
        return function() {
            var context = this;
            var args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                func.apply(context, args);
            }, wait);
        };
    };

    /**
     * Flash message auto-dismiss after 5 seconds.
     */
    document.addEventListener('DOMContentLoaded', function() {
        var messages = document.querySelectorAll('.messages__item');
        messages.forEach(function(msg) {
            setTimeout(function() {
                msg.style.opacity = '0';
                msg.style.transition = 'opacity 0.5s';
                setTimeout(function() { msg.remove(); }, 500);
            }, 5000);
        });
    });
})();
