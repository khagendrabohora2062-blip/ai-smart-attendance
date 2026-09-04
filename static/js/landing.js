(function () {

    "use strict";


    const navbar =
        document.querySelector(
            ".custom-navbar"
        );


    const backToTop =
        document.getElementById(
            "backToTop"
        );


    const revealItems =
        document.querySelectorAll(
            ".reveal"
        );


    const counters =
        document.querySelectorAll(
            ".counter[data-target]"
        );


    // =====================================================
    // NAVBAR
    // =====================================================

    const updateNavbar = () => {

        if (navbar) {

            navbar.classList.toggle(
                "scrolled",
                window.scrollY > 25
            );

        }


        if (backToTop) {

            backToTop.classList.toggle(
                "show",
                window.scrollY > 450
            );

        }

    };


    window.addEventListener(
        "scroll",
        updateNavbar,
        {
            passive: true
        }
    );


    updateNavbar();


    // =====================================================
    // BACK TO TOP
    // =====================================================

    if (backToTop) {

        backToTop.addEventListener(
            "click",
            () => {

                window.scrollTo({
                    top: 0,
                    behavior: "smooth"
                });

            }
        );

    }


    // =====================================================
    // SCROLL REVEAL
    // =====================================================

    const revealObserver =
        "IntersectionObserver" in window

            ? new IntersectionObserver(
                (
                    entries,
                    observer
                ) => {

                    entries.forEach(
                        (entry) => {

                            if (
                                !entry.isIntersecting
                            ) {
                                return;
                            }


                            entry.target.classList.add(
                                "show"
                            );


                            observer.unobserve(
                                entry.target
                            );

                        }
                    );

                },
                {
                    threshold: 0.12,

                    rootMargin:
                        "0px 0px -40px 0px"
                }
            )

            : null;


    revealItems.forEach(
        (item) => {

            if (revealObserver) {

                revealObserver.observe(
                    item
                );

            } else {

                item.classList.add(
                    "show"
                );

            }

        }
    );


    // =====================================================
    // COUNTER ANIMATION
    // =====================================================

    const animateCounter =
        (element) => {

            const target =
                Math.max(
                    0,
                    Number(
                        element.dataset.target || 0
                    )
                );


            if (
                !Number.isFinite(
                    target
                )
            ) {

                element.textContent = "0";

                return;
            }


            if (target === 0) {

                element.textContent = "0";

                return;
            }


            const duration = 1100;

            const start =
                performance.now();


            const tick =
                (now) => {

                    const progress =
                        Math.min(
                            (
                                now - start
                            ) / duration,
                            1
                        );


                    const eased =
                        1 -
                        Math.pow(
                            1 - progress,
                            3
                        );


                    element.textContent =
                        Math.floor(
                            target * eased
                        ).toLocaleString();


                    if (
                        progress < 1
                    ) {

                        requestAnimationFrame(
                            tick
                        );

                    } else {

                        element.textContent =
                            target.toLocaleString();

                    }

                };


            requestAnimationFrame(
                tick
            );

        };


    if (counters.length) {

        const counterObserver =
            "IntersectionObserver" in window

                ? new IntersectionObserver(
                    (
                        entries,
                        observer
                    ) => {

                        entries.forEach(
                            (entry) => {

                                if (
                                    !entry.isIntersecting
                                ) {
                                    return;
                                }


                                animateCounter(
                                    entry.target
                                );


                                observer.unobserve(
                                    entry.target
                                );

                            }
                        );

                    },
                    {
                        threshold: 0.4
                    }
                )

                : null;


        counters.forEach(
            (counter) => {

                if (counterObserver) {

                    counterObserver.observe(
                        counter
                    );

                } else {

                    animateCounter(
                        counter
                    );

                }

            }
        );

    }


    // =====================================================
    // SAME-PAGE NAVIGATION
    // =====================================================

    document
        .querySelectorAll(
            'a[href^="#"]'
        )
        .forEach(
            (link) => {

                link.addEventListener(
                    "click",
                    (event) => {

                        const selector =
                            link.getAttribute(
                                "href"
                            );


                        if (
                            !selector ||
                            selector === "#"
                        ) {
                            return;
                        }


                        const target =
                            document.querySelector(
                                selector
                            );


                        if (!target) {
                            return;
                        }


                        event.preventDefault();


                        target.scrollIntoView({
                            behavior: "smooth",
                            block: "start"
                        });


                        const nav =
                            document.querySelector(
                                ".navbar-collapse.show"
                            );


                        if (
                            nav &&
                            window.bootstrap
                        ) {

                            const instance =
                                window.bootstrap.Collapse
                                    .getInstance(
                                        nav
                                    )
                                ||
                                new window.bootstrap.Collapse(
                                    nav,
                                    {
                                        toggle: false
                                    }
                                );


                            instance.hide();

                        }

                    }
                );

            }
        );


    // =====================================================
    // ACTIVE LANDING NAVIGATION
    // =====================================================

    const sectionLinks =
        Array.from(
            document.querySelectorAll(
                '.custom-navbar .nav-link[href^="#"]'
            )
        );


    const sections =
        sectionLinks
            .map(
                (link) =>
                    document.querySelector(
                        link.getAttribute(
                            "href"
                        )
                    )
            )
            .filter(Boolean);


    if (
        sections.length &&
        "IntersectionObserver" in window
    ) {

        const navObserver =
            new IntersectionObserver(
                (entries) => {

                    entries.forEach(
                        (entry) => {

                            if (
                                !entry.isIntersecting
                            ) {
                                return;
                            }


                            const id =
                                `#${entry.target.id}`;


                            sectionLinks.forEach(
                                (link) => {

                                    link.classList.toggle(
                                        "active",
                                        link.getAttribute(
                                            "href"
                                        ) === id
                                    );

                                }
                            );

                        }
                    );

                },
                {
                    rootMargin:
                        "-35% 0px -55% 0px",

                    threshold: 0
                }
            );


        sections.forEach(
            (section) => {

                navObserver.observe(
                    section
                );

            }
        );

    }


    // =====================================================
    // MOBILE MENU CLOSE
    // =====================================================

    document
        .querySelectorAll(
            ".custom-navbar .nav-link:not([href^='#'])"
        )
        .forEach(
            (link) => {

                link.addEventListener(
                    "click",
                    () => {

                        const nav =
                            link.closest(
                                ".navbar-collapse.show"
                            );


                        if (
                            nav &&
                            window.bootstrap
                        ) {

                            const instance =
                                window.bootstrap.Collapse
                                    .getInstance(
                                        nav
                                    )
                                ||
                                new window.bootstrap.Collapse(
                                    nav,
                                    {
                                        toggle: false
                                    }
                                );


                            instance.hide();

                        }

                    }
                );

            }
        );


    // =====================================================
    // TOOLTIP SUPPORT
    // =====================================================

    if (window.bootstrap) {

        document
            .querySelectorAll(
                '[data-bs-toggle="tooltip"]'
            )
            .forEach(
                (element) => {

                    new window.bootstrap.Tooltip(
                        element
                    );

                }
            );

    }


    // =====================================================
    // JS READY
    // =====================================================

    document.documentElement.classList.add(
        "landing-js-ready"
    );

})();