// ====== EC2 BACKEND URL ======
// Replace this with your EC2 public IP when deploying on EC2
const API_URL = "http://100.25.118.46:5000";
// =============================

let currentUser = null;
let currentUserName = null;

window.onload = () => {
    const savedUser = localStorage.getItem('currentUser');
    const savedName = localStorage.getItem('currentUserName');

    if (savedUser) {
        currentUser = savedUser;
        currentUserName = savedName;

        document.getElementById('login-screen').classList.add('hidden-screen');
        document.getElementById('main-screen').classList.remove('hidden-screen');

        const displayName = currentUserName || currentUser;
        document.getElementById('user-email-display').innerText = displayName;
        document.getElementById('user-avatar').innerText = displayName.charAt(0).toUpperCase();

        loadSubscriptions();
    }
};

async function apiRequest(endpoint, method, body = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_URL}${endpoint}`, options);
    return response.json();
}

async function login() {
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const messageEl = document.getElementById('login-message');

    if (!email || !password) {
        messageEl.innerText = "Please enter email and password!";
        messageEl.classList.remove('hidden-screen');
        return;
    }

    messageEl.innerText = "Connecting to EC2 backend...";
    messageEl.classList.remove('hidden-screen');

    try {
        const res = await apiRequest('/api/login', 'POST', {
            email,
            password
        });

        if (res.message === 'Login successful.') {
            currentUser = email;
            currentUserName = res.user && res.user.username
                ? res.user.username
                : email.split('@')[0];

            localStorage.setItem('currentUser', currentUser);
            localStorage.setItem('currentUserName', currentUserName);

            document.getElementById('login-screen').classList.add('hidden-screen');
            document.getElementById('main-screen').classList.remove('hidden-screen');

            const displayName = currentUserName || currentUser;
            document.getElementById('user-email-display').innerText = displayName;
            document.getElementById('user-avatar').innerText = displayName.charAt(0).toUpperCase();

            loadSubscriptions();
        } else {
            messageEl.innerText = res.error || res.message || "Login failed.";
        }
    } catch (e) {
        messageEl.innerText = "Failed to connect to EC2 backend. Check API_URL and EC2 security group.";
        console.error(e);
    }
}

async function register() {
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const confirmPassword = document.getElementById('reg-confirm-password').value;
    const messageEl = document.getElementById('register-message');

    if (!email || !password || !confirmPassword) {
        messageEl.innerText = "Please fill in all fields!";
        messageEl.classList.remove('hidden-screen');
        return;
    }

    if (password !== confirmPassword) {
        messageEl.innerText = "Passwords do not match!";
        messageEl.classList.remove('hidden-screen');
        return;
    }

    const username = email.split('@')[0];

    messageEl.innerText = "Registering...";
    messageEl.classList.remove('hidden-screen');

    try {
        const res = await apiRequest('/api/register', 'POST', {
            username,
            email,
            password
        });

        if (res.message === 'User registered successfully.') {
            document.getElementById('login-email').value = email;
            document.getElementById('login-password').value = password;

            showLogin();

            const loginMsg = document.getElementById('login-message');
            loginMsg.innerText = "Registration successful! Please login.";
            loginMsg.classList.remove('hidden-screen');

            document.getElementById('reg-password').value = '';
            document.getElementById('reg-confirm-password').value = '';
        } else {
            messageEl.innerText = res.error || res.message || "Registration failed.";
        }
    } catch (e) {
        messageEl.innerText = "Failed to connect to EC2 backend.";
        console.error(e);
    }
}

function showRegister() {
    document.getElementById('login-screen').classList.add('hidden-screen');
    document.getElementById('register-screen').classList.remove('hidden-screen');
}

function showLogin() {
    document.getElementById('register-screen').classList.add('hidden-screen');
    document.getElementById('login-screen').classList.remove('hidden-screen');
}

function logout() {
    currentUser = null;
    currentUserName = null;

    localStorage.removeItem('currentUser');
    localStorage.removeItem('currentUserName');

    document.getElementById('main-screen').classList.add('hidden-screen');
    document.getElementById('login-screen').classList.remove('hidden-screen');

    document.getElementById('login-email').value = '';
    document.getElementById('login-password').value = '';
    document.getElementById('login-message').classList.add('hidden-screen');
    document.getElementById('music-results').innerHTML = '';
}

function escapeForButton(value) {
    return String(value).replace(/'/g, "\\'");
}

async function searchMusic() {
    const title = document.getElementById('search-title').value;
    const artist = document.getElementById('search-artist').value;
    const album = document.getElementById('search-album').value;
    const year = document.getElementById('search-year').value;

    const container = document.getElementById('music-results');
    container.innerHTML = '';

    const params = new URLSearchParams();

    if (title) params.append('title', title);
    if (artist) params.append('artist', artist);
    if (album) params.append('album', album);
    if (year) params.append('year', year);

    const queryString = params.toString() ? `?${params.toString()}` : '';

    if (!queryString) {
        container.innerHTML = '<p>Please search using artist, album, or artist + year.</p>';
        return;
    }

    try {
        const res = await apiRequest(`/api/query${queryString}`, 'GET');

        if (res.error || res.message) {
            container.innerHTML = `<p style="color: #ff4b4b;">API Error: ${res.error || res.message}</p>`;
            return;
        }

        const songsList = Array.isArray(res) ? res : res.songs;

        if (!songsList || songsList.length === 0) {
            container.innerHTML = '<p>No results found in DynamoDB.</p>';
            return;
        }

        songsList.forEach(song => {
            const safeArtist = escapeForButton(song.artist);
            const safeTitle = escapeForButton(song.title);

            container.innerHTML += `
                <div class="neo-card song-card">
                    <div class="song-card-img-container">
                        <img src="${song.img_url}" alt="${song.title}">
                    </div>
                    <div>
                        <h4>${song.title}</h4>
                        <p>${song.artist} • ${song.year}</p>
                        <button 
                            type="button" 
                            onclick="subscribe('${safeArtist}', '${safeTitle}')" 
                            class="neo-btn primary w-full">
                            SUBSCRIBE
                        </button>
                    </div>
                </div>
            `;
        });
    } catch (e) {
        container.innerHTML = '<p style="color: #ff4b4b;">Failed to load music results.</p>';
        console.error(e);
    }
}

async function loadSubscriptions() {
    const container = document.getElementById('user-subscriptions');
    container.innerHTML = '';

    try {
        const res = await apiRequest(`/api/subscriptions?email=${encodeURIComponent(currentUser)}`, 'GET');

        if (res.error || res.message) {
            container.innerHTML = `<p style="color: #ff4b4b;">API Error: ${res.error || res.message}</p>`;
            return;
        }

        const songsList = Array.isArray(res) ? res : res.songs;

        if (!songsList || songsList.length === 0) {
            container.innerHTML = '<p>You have no active subscriptions.</p>';
            return;
        }

        songsList.forEach(song => {
            const safeArtist = escapeForButton(song.artist);
            const safeTitle = escapeForButton(song.title);

            container.innerHTML += `
                <div class="sub-item" style="padding: 0.5rem; justify-content: space-between;">
                    <div style="display: flex; align-items: center; min-width: 0;">
                        <img 
                            src="${song.img_url}" 
                            alt="${song.title}" 
                            class="sub-img" 
                            style="width: 2.5rem; height: 2.5rem; border: 2px solid var(--ink-black);">
                        <div class="sub-details">
                            <h4 style="font-size: 1rem; margin-bottom: 0;">${song.title}</h4>
                            <p style="font-size: 0.75rem;">${song.artist}</p>
                        </div>
                    </div>
                    <button 
                        type="button" 
                        onclick="removeSubscription('${safeArtist}', '${safeTitle}')" 
                        class="neo-btn ghost sub-remove" 
                        style="width: 2rem; height: 2rem; padding: 0; font-size: 1rem;">
                        X
                    </button>
                </div>
            `;
        });
    } catch (e) {
        container.innerHTML = '<p style="color: #ff4b4b;">Failed to load subscriptions.</p>';
        console.error(e);
    }
}

async function subscribe(artist, title) {
    try {
        await apiRequest('/api/subscribe', 'POST', {
            email: currentUser,
            artist: artist,
            title: title
        });

        loadSubscriptions();
    } catch (e) {
        console.error("Subscription failed:", e);
    }
}

async function removeSubscription(artist, title) {
    try {
        await apiRequest('/api/unsubscribe', 'POST', {
            email: currentUser,
            artist: artist,
            title: title
        });

        loadSubscriptions();
    } catch (e) {
        console.error("Unsubscribe failed:", e);
    }
}