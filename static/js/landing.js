/* ==========================================================
AI SMART ATTENDANCE SYSTEM
Landing Page JavaScript
========================================================== */

// =========================================
// Sticky Navbar
// =========================================

const navbar = document.querySelector(".custom-navbar");

window.addEventListener("scroll", () => {

    if (window.scrollY > 50) {

        navbar.classList.add("scrolled");

    } else {

        navbar.classList.remove("scrolled");

    }

});

// =========================================
// Back To Top Button
// =========================================

const backToTop = document.getElementById("backToTop");

window.addEventListener("scroll", () => {

    if (window.scrollY > 400) {

        backToTop.style.display = "block";

    } else {

        backToTop.style.display = "none";

    }

});

backToTop.addEventListener("click", () => {

    window.scrollTo({

        top: 0,

        behavior: "smooth"

    });

});

// =========================================
// Scroll Reveal Animation
// =========================================

const revealItems = document.querySelectorAll(

    ".feature-card, .step-card, .glass-card, .tech-card, .testimonial-card"

);

const reveal = () => {

    revealItems.forEach(item => {

        const top = item.getBoundingClientRect().top;

        const windowHeight = window.innerHeight;

        if (top < windowHeight - 80) {

            item.classList.add("show");

        }

    });

};

window.addEventListener("scroll", reveal);

window.addEventListener("load", reveal);

// =========================================
// Counter Animation
// =========================================

const counters = document.querySelectorAll(".counter");

const animateCounter = counter => {

    const target = Number(counter.innerText);

    let count = 0;

    const speed = Math.max(1, Math.ceil(target / 80));

    const update = () => {

        if (count < target) {

            count += speed;

            if (count > target) count = target;

            counter.innerText = count;

            requestAnimationFrame(update);

        }

    };

    update();

};

const counterObserver = new IntersectionObserver(entries => {

    entries.forEach(entry => {

        if (entry.isIntersecting) {

            animateCounter(entry.target);

            counterObserver.unobserve(entry.target);

        }

    });

});

counters.forEach(counter => {

    counterObserver.observe(counter);

});

// =========================================
// Active Navbar Link
// =========================================

const sections = document.querySelectorAll("section");

const navLinks = document.querySelectorAll(".nav-link");

window.addEventListener("scroll", () => {

    let current = "";

    sections.forEach(section => {

        const top = section.offsetTop - 120;

        const height = section.clientHeight;

        if (pageYOffset >= top) {

            current = section.getAttribute("id");

        }

    });

    navLinks.forEach(link => {

        link.classList.remove("active");

        const href = link.getAttribute("href");

        if (href === "#" + current) {

            link.classList.add("active");

        }

    });

});

// =========================================
// Smooth Fade-In on Load
// =========================================

window.addEventListener("load", () => {

    document.body.style.opacity = "1";

});

// =========================================
// Console Message
// =========================================

console.log(
    "AI Smart Attendance System Loaded Successfully 🚀"
);