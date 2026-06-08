// Тест: Ако видиш този прозорец при зареждане, значи файлът е свързан!
alert("JavaScript е зареден!"); 

async function handleAuth(type) {
    console.log("Натиснат бутон: " + type);
    
    let user, pass;
    if (type === 'register') {
        user = document.getElementById('reg-user').value;
        pass = document.getElementById('reg-pass').value;
    } else {
        user = document.getElementById('login-user').value;
        pass = document.getElementById('login-pass').value;
    }

    if (!user || !pass) {
        alert("Моля, попълнете полетата!");
        return;
    }

    try {
        const response = await fetch('/handle_auth', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ action: type, username: user, password: pass })
        });
        const result = await response.json();
        if (result.success) {
            window.location.href = "/";
        } else {
            alert(result.message);
        }
    } catch (err) {
        console.error("Грешка:", err);
    }
}