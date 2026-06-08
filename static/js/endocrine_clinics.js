/* =========================
   MAP
========================= */
const map = L.map('map').setView([42.7,23.3],7);
L.tileLayer(
'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
{
    attribution:'© OpenStreetMap'
}
).addTo(map);
let clinics = [];
let markers = [];
/* =========================
   TIME SLOTS
========================= */
const TIMES = [
    "09:00","10:00","11:00",
    "12:00","13:00","14:00",
    "15:00","16:00","17:00"
];
let selectedSlots = {};
/* =========================
   AUTH
========================= */
async function checkAuth(){
    try{
        const res = await fetch("/me",{
            credentials:"include"
        });
        const data = await res.json();
        if(!data.logged_in){
            window.location.href="/login";
        }
    }catch(e){
        window.location.href="/login";
    }
}
checkAuth();
/* =========================
   LOAD DOCTORS
========================= */
async function loadDoctors(){
    try{
        const res = await fetch(
            "/api/doctors",
            {
                credentials:"include"
            }
        );
        clinics = await res.json();
        renderClinics(clinics);
        loadMarkers(clinics);
    }catch(err){
        console.error(err);
        document.getElementById("clinicList").innerHTML =
        `<p>Грешка при зареждане на лекарите.</p>`;
    }
}
loadDoctors();
/* =========================
   MAP MARKERS
========================= */
function loadMarkers(data){
    markers.forEach(m => map.removeLayer(m));
    markers = [];
    data.forEach(c => {
        if(!c.latitude || !c.longitude)
            return;
        const marker = L.marker([
            c.latitude,
            c.longitude
        ])
        .addTo(map)
        .bindPopup(`
            <b>${c.full_name}</b><br>
            ${c.specialty}<br>
            ${c.city}
        `);
        markers.push(marker);
    });
}
/* =========================
   RENDER CLINICS
========================= */
function renderClinics(data){
    const list =
    document.getElementById("clinicList");
    if(!data.length){
        list.innerHTML =
        `<p>Няма намерени специалисти.</p>`;
        return;
    }
    list.innerHTML = data.map(c => `
        <div class="clinic-card">
            <h3>${c.full_name}</h3>
            <p><b>${c.specialty}</b></p>
            <p>📍 ${c.city}</p>
            <p>🏥 ${c.hospital || ""}</p>
            <input
                type="date"
                id="date-${c.id}"
                onchange="renderSlots(${c.id})"
            >
            <div
                id="slots-${c.id}"
                style="margin-top:10px;">
            </div>
            <button
                onclick="bookAppointment(${c.id})"
                style="margin-top:15px;width:100%;">
                📅 Запази час
            </button>
            <div
                class="success"
                id="success-${c.id}">
            </div>
        </div>
    `).join('');
}
/* =========================
   RENDER SLOTS
========================= */
async function renderSlots(doctorId){
    const date =
    document.getElementById(`date-${doctorId}`).value;
    const container =
    document.getElementById(`slots-${doctorId}`);
    if(!date){
        container.innerHTML = "";
        return;
    }
    try{
        const res = await fetch(
            `/doctor-availability/${doctorId}/${date}`,
            {
                credentials:"include"
            }
        );
        const data = await res.json();
        const booked = data.booked || [];
        container.innerHTML = TIMES.map(time => {
            const isBooked =
            booked.includes(time);
            const isSelected =
            selectedSlots[doctorId] === time;
            return `
                <button
                    class="
                        slot-btn
                        ${isBooked ? 'booked-slot' : 'free-slot'}
                        ${isSelected ? 'selected-slot' : ''}
                    "
                    onclick="
                        selectSlot(${doctorId}, '${time}')
                    "
                    ${isBooked ? "disabled" : ""}
                >
                    ${isBooked ? "Зает" : time}
                </button>
            `;
        }).join('');
    }catch(err){
        console.error(err);
        container.innerHTML =
        `<p>Грешка при зареждане.</p>`;
    }
}
/* =========================
   SELECT SLOT
========================= */
function selectSlot(doctorId,time){
    selectedSlots[doctorId] = time;
    renderSlots(doctorId);
}
/* =========================
   BOOK
========================= */
async function bookAppointment(doctorId){
    const date =
    document.getElementById(`date-${doctorId}`).value;
    if(!date){
        alert("Изберете дата!");
        return;
    }
    const selectedTime =
    selectedSlots[doctorId];
    if(!selectedTime){
        alert("Изберете час!");
        return;
    }
    try{
        const res = await fetch(
            "/book-appointment",
            {
                method:"POST",
                headers:{
                    "Content-Type":"application/json"
                },
                credentials:"include",
                body:JSON.stringify({
                    doctor_id:doctorId,
                    date:date,
                    time:selectedTime
                })
            }
        );
        const data = await res.json();
        if(data.success){
            const successBox =
            document.getElementById(`success-${doctorId}`);
            successBox.style.display = "block";
            successBox.innerText =
            `✅ Успешно запазен час: ${selectedTime}`;
            delete selectedSlots[doctorId];
            await renderSlots(doctorId);
        }else{
            alert(data.error || "Грешка");
        }
    }catch(err){
        console.error(err);
        alert("Сървърна грешка");
    }
}
/* =========================
   SEARCH
========================= */


function searchClinic(){


    const value =
    document.getElementById(
        "searchInput"
    ).value.toLowerCase();


    const filtered = clinics.filter(c =>

        (c.full_name || "")
        .toLowerCase()
        .includes(value)
        ||
        (c.city || "")
        .toLowerCase()
        .includes(value)
        ||
        (c.specialty || "")
        .toLowerCase()
        .includes(value)
    );
    renderClinics(filtered);
    loadMarkers(filtered);
}
/* =========================
   FILTER CITY
========================= */
function filterByCity(){
    const city =
    document.getElementById(
        "cityFilter"
    ).value;
    if(city === "all"){
        renderClinics(clinics);
        loadMarkers(clinics);
        return;
    }
    const filtered =
    clinics.filter(c => c.city === city);
    renderClinics(filtered);
    loadMarkers(filtered);
}
/* =========================
   FIND NEAREST
========================= */
function findNearest(){
    navigator.geolocation.getCurrentPosition(pos => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        let nearest = null;
        let min = 99999;
        clinics.forEach(c => {
            if(!c.latitude || !c.longitude)
                return;
            const d =
            getDistance(
                lat,
                lng,
                c.latitude,
                c.longitude
            );
            if(d < min){
                min = d;
                nearest = c;
            }
        });
        if(!nearest) return;
        alert(
            `Най-близък доктор:\n\n${nearest.full_name}`
        );
        map.setView([
            nearest.latitude,
            nearest.longitude
        ],12);
    },() => {
        alert("Разрешете достъп до локация");
    });
}
/* =========================
   DISTANCE
========================= */
function getDistance(a,b,c,d){
    const R = 6371;
    const dLat =
    (c-a) * Math.PI/180;
    const dLon =
    (d-b) * Math.PI/180;
    const x =
    Math.sin(dLat/2)**2 +
    Math.cos(a*Math.PI/180) *
    Math.cos(c*Math.PI/180) *
    Math.sin(dLon/2)**2;
    return 2 * R *
    Math.atan2(
        Math.sqrt(x),
        Math.sqrt(1-x)
    );
}
function showLoading(state){
    document.getElementById("loading").style.display =
        state ? "block" : "none";
}