// static/js/creators_list.js

function storeReferrerAndRedirect(url) {
    sessionStorage.setItem('referrer', window.location.href);
    window.location.href = url;
}

function goToDashboard(username) {
    sessionStorage.setItem('referrer-from-subscriptions', window.location.href);
    window.location.href = `/dashboard/${username}`;
}
