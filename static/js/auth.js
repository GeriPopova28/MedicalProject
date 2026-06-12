let login = true;


    // Слушател за натискане на Enter в полетата
    document.getElementById("username").addEventListener("keypress", handleEnter);
    document.getElementById("password").addEventListener("keypress", handleEnter);


    function handleEnter(e) {
        if (e.key === "Enter") {
            submitForm();
        }
    }


    // Логика за динамично следене силата на паролата
    document.getElementById("password").addEventListener("input", function(e) {
        if(login) return; // Спираме проверката, ако сме в режим Вход
       
        const val = e.target.value;
        const bar = document.getElementById("strengthBar");
        const text = document.getElementById("strengthText");
       
        let score = 0;
        if (val.length >= 6) score++;
        if (/[A-Z]/.test(val)) score++;
        if (/[0-9]/.test(val)) score++;
        if (/[^A-Za-z0-9]/.test(val)) score++;


        if (val.length === 0) {
            bar.style.width = "0%";
            text.innerText = "Сила на паролата:";
        } else if (score <= 1) {
            bar.style.width = "25%";
            bar.style.background = "#ef4444"; 
            text.innerText = "Слаба парола";
        } else if (score === 2 || score === 3) {
            bar.style.width = "60%";
            bar.style.background = "#f59e0b";
            text.innerText = "Средна парола";
        } else {
            bar.style.width = "100%";
            bar.style.background = "#10b981";
            text.innerText = "Силна парола";
        }
    });


    function toggle() {
        login = !login;
        document.getElementById("title").innerText = login ? "MedAI Login" : "Регистрация";
        document.getElementById("roleBox").style.display = login ? "none" : "block";
        document.getElementById("strengthWrapper").style.display = login ? "none" : "block";
        document.getElementById("switchText").innerText = login ? "Нямаш акаунт?" : "Вече имаш профил?";
        document.getElementById("toggleBtn").innerText = login ? "Регистрация" : "Вход";
        document.getElementById("loginBtn").innerText = login ? "Вход" : "Регистрация";
       
        // Нулиране на паролата и бар-а при суич
        document.getElementById("password").value = "";
        document.getElementById("strengthBar").style.width = "0%";
        document.getElementById("strengthText").innerText = "Сила на паролата:";
    }


    function submitForm() {
    const usernameInput = document.getElementById("username").value;
    const passwordInput = document.getElementById("password").value;

    const isRegister = document.getElementById("loginBtn").innerText.trim() === "Регистрация";
    const actionType = isRegister ? "register" : "login";

    let selectedRole = "Patient"; 
    if (isRegister) {
        const roleRadio = document.querySelector('input[name="role"]:checked');
        if (roleRadio) {
            selectedRole = roleRadio.value;
        }
    }

    if (!usernameInput || !passwordInput) {
        alert("Моля, попълнете всички полета!");
        return;
    }

    fetch('/handle_auth', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: usernameInput,
            password: passwordInput,
            action: actionType,  
            role: selectedRole   
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (actionType === "register") {
                alert(data.message || "Регистрацията е успешна! Сега можете да влезете.");
                toggle(); 
            } else {
                window.location.href = '/'; 
            }
        } else {
            alert("Грешка: " + data.error);
        }
    })
    .catch(err => {
        console.error("Грешка при аутентификация:", err);
        alert("Възникна грешка при връзката със сървъра.");
    });
}


    function showError(msg) {
        const oldBox = document.querySelector(".toast-error");
        if(oldBox) oldBox.remove();


        const box = document.createElement("div");
        box.className = "toast-error";
        box.innerText = msg;


        box.style.position = "fixed";
        box.style.top = "20px";
        box.style.right = "20px";
        box.style.padding = "12px 20px";
        box.style.background = "rgba(239, 68, 68, 0.95)";
        box.style.color = "white";
        box.style.borderRadius = "10px";
        box.style.boxShadow = "0 10px 30px rgba(0,0,0,0.3)";
        box.style.zIndex = "9999";
        box.style.fontFamily = "'Inter', sans-serif";


        document.body.appendChild(box);


        setTimeout(() => {
            box.remove();
        }, 3000);
    }
