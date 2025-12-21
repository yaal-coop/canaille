// Convert base64url string to ArrayBuffer for WebAuthn API
function base64urlToBuffer(base64url) {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

// Convert ArrayBuffer to base64url string for JSON transport
function bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

// Display error: show predefined div if ID exists, otherwise show dynamic message
function showError(messageDiv, errorIdOrMessage) {
    const allErrors = document.querySelectorAll('.error-message');
    allErrors.forEach(div => div.classList.add('hidden'));

    messageDiv.classList.add('hidden');

    const errorDiv = document.getElementById(errorIdOrMessage);
    if (errorDiv) {
        errorDiv.classList.remove('hidden');
    } else {
        const mainErrorDiv = document.getElementById('webauthn-error');
        const mainErrorMessage = document.getElementById('webauthn-error-message');
        mainErrorMessage.textContent = errorIdOrMessage;
        mainErrorDiv.classList.remove('hidden');
    }
}

// Hide all error messages and restore the main instruction message
function hideError(messageDiv) {
    const allErrors = document.querySelectorAll('.error-message');
    allErrors.forEach(div => div.classList.add('hidden'));

    messageDiv.classList.remove('hidden');
}

// Entry point: detect registration or authentication context and initialize
function initFido() {
    // Detect context based on button presence
    const registerButton = document.getElementById('webauthn-register');
    const authenticateButton = document.getElementById('webauthn-authenticate');

    if (registerButton) {
        initWebAuthn('register', registerButton);
    } else if (authenticateButton) {
        initWebAuthn('authenticate', authenticateButton);
    }
}

// Setup WebAuthn flow: parse server options, handle button click, communicate with server
function initWebAuthn(mode, button) {
    const messageDiv = document.getElementById('webauthn-message');
    const optionsInput = document.getElementById('webauthn-options');

    if (!button || !optionsInput) {
        console.error('WebAuthn elements not found');
        return;
    }

    // Prevent double initialization
    if (button.dataset.initialized === 'true') {
        return;
    }
    button.dataset.initialized = 'true';

    // Security key OTP detection
    let keyPressTimestamps = [];
    let otpWarningShown = false;
    let detectionActive = true;

    // Detect security key OTP mode: warn user if rapid keypresses suggest OTP instead of FIDO2
    function detectSecurityKeyOTP(event) {
        if (!detectionActive || otpWarningShown) return;

        // Ignore modifier keys
        if (event.key.length > 1 && event.key !== 'Enter') return;

        const now = Date.now();
        keyPressTimestamps.push(now);

        // Keep only last 50 keypresses
        if (keyPressTimestamps.length > 50) {
            keyPressTimestamps.shift();
        }

        // Check if we have a rapid sequence (>= 10 chars in < 200ms)
        if (keyPressTimestamps.length >= 10) {
            const oldest = keyPressTimestamps[keyPressTimestamps.length - 10];
            const duration = now - oldest;

            if (duration < 200) {
                showError(messageDiv, 'otp');
                otpWarningShown = true;
                detectionActive = false;
            }
        }
    }

    // Start listening for security key OTP
    document.addEventListener('keydown', detectSecurityKeyOTP);

    // Parse options from server
    let options;
    try {
        options = JSON.parse(optionsInput.value);
    } catch (e) {
        showError(messageDiv, 'parse');
        return;
    }

    // Convert base64url strings to ArrayBuffers
    options.challenge = base64urlToBuffer(options.challenge);

    if (mode === 'register') {
        options.user.id = base64urlToBuffer(options.user.id);
        if (options.excludeCredentials) {
            options.excludeCredentials = options.excludeCredentials.map(cred => ({
                ...cred,
                id: base64urlToBuffer(cred.id)
            }));
        }
    } else {
        if (options.allowCredentials) {
            options.allowCredentials = options.allowCredentials.map(cred => ({
                ...cred,
                id: base64urlToBuffer(cred.id)
            }));
        }
    }

    button.addEventListener('click', async function() {
        try {
            hideError(messageDiv);
            detectionActive = false;
            button.disabled = true;
            button.classList.add('loading');

            let credential;
            if (mode === 'register') {
                credential = await navigator.credentials.create({ publicKey: options });
            } else {
                credential = await navigator.credentials.get({ publicKey: options });
            }

            // Prepare response for server
            let response;
            if (mode === 'register') {
                response = {
                    credential: {
                        id: credential.id,
                        rawId: bufferToBase64url(credential.rawId),
                        type: credential.type,
                        response: {
                            attestationObject: bufferToBase64url(credential.response.attestationObject),
                            clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
                            transports: credential.response.getTransports ? credential.response.getTransports() : []
                        }
                    }
                };
            } else {
                response = {
                    id: credential.id,
                    rawId: bufferToBase64url(credential.rawId),
                    type: credential.type,
                    response: {
                        authenticatorData: bufferToBase64url(credential.response.authenticatorData),
                        clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
                        signature: bufferToBase64url(credential.response.signature),
                        userHandle: credential.response.userHandle ? bufferToBase64url(credential.response.userHandle) : null
                    }
                };
            }

            // Send to server
            const result = await fetch(window.location.href, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(response)
            });

            const data = await result.json();

            if (data.success && data.redirect) {
                window.location.href = data.redirect;
            } else {
                // Server error - use dynamic message
                showError(messageDiv, data.error);
                button.disabled = false;
                button.classList.remove('loading');
            }
        } catch (error) {
            console.error('WebAuthn error:', error);
            showError(messageDiv, error.name ? error.name.toLowerCase() : 'unknown');
            button.disabled = false;
            button.classList.remove('loading');
        }
    });
}

// Initialize on page load and HTMX page swaps
if (typeof htmx !== 'undefined') {
    htmx.onLoad(initFido);
    // Also call for already loaded content
    initFido();
} else {
    // Fallback when htmx is not available
    document.addEventListener('DOMContentLoaded', initFido);
}
