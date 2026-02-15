/**
 * Utilidades de Animación con Anime.js Timeline
 * SkyPulse - Sistema de Monitoreo Meteorológico
 * 
 * Proporciona funciones reutilizables para animaciones coordinadas
 * usando Anime.js Timeline API
 * 
 * Documentación: https://animejs.com/documentation/timeline/
 */

(function(window) {
    'use strict';

    // Verificar que anime.js esté disponible
    if (typeof anime === 'undefined') {
        console.error('[AnimeUtils] anime.js no está cargado. Cargue anime.js antes de usar estas utilidades.');
        return;
    }

    /**
     * Anima la entrada de una alerta en el stack
     * @param {HTMLElement} alertElement - Elemento de la alerta
     * @param {number} index - Índice para efecto stagger
     * @returns {Object} Timeline de anime.js
     */
    function animateAlertIn(alertElement, index = 0) {
        if (!alertElement) return null;

        const timeline = anime.timeline({
            easing: 'easeOutExpo',
            duration: 300,
            autoplay: true
        });

        timeline.add({
            targets: alertElement,
            translateX: [100, 0],
            opacity: [0, 1],
            duration: 300,
            delay: index * 50, // Stagger effect
            easing: 'easeOutExpo'
        });

        // Si es nivel 4, agregar pulso continuo
        if (alertElement.classList.contains('level-4')) {
            timeline.add({
                targets: alertElement,
                scale: [1, 1.02],
                duration: 2000,
                loop: true,
                easing: 'easeInOutSine',
                direction: 'alternate'
            });
        }

        return timeline;
    }

    /**
     * Anima la salida de una alerta
     * @param {HTMLElement} alertElement - Elemento de la alerta
     * @param {Function} callback - Callback opcional al completar
     * @returns {Object} Animación de anime.js
     */
    function animateAlertOut(alertElement, callback = null) {
        if (!alertElement) return null;

        return anime({
            targets: alertElement,
            translateX: [0, 100],
            opacity: [1, 0],
            duration: 200,
            easing: 'easeInExpo',
            complete: () => {
                if (callback) callback();
                else alertElement.remove();
            }
        });
    }

    /**
     * Anima la aparición de un tooltip
     * @param {HTMLElement} tooltipElement - Elemento del tooltip
     * @param {string} position - Posición del tooltip ('top', 'bottom', 'left', 'right')
     * @returns {Object} Animación de anime.js
     */
    function animateTooltipIn(tooltipElement, position = 'top') {
        if (!tooltipElement) return null;

        const fromPositions = {
            top: { translateY: [-10, 0] },
            bottom: { translateY: [10, 0] },
            left: { translateX: [-10, 0] },
            right: { translateX: [10, 0] }
        };

        const animation = fromPositions[position] || fromPositions.top;

        return anime({
            targets: tooltipElement,
            ...animation,
            opacity: [0, 1],
            scale: [0.95, 1],
            duration: 200,
            easing: 'easeOutExpo'
        });
    }

    /**
     * Anima la desaparición de un tooltip
     * @param {HTMLElement} tooltipElement - Elemento del tooltip
     * @param {Function} callback - Callback opcional al completar
     * @returns {Object} Animación de anime.js
     */
    function animateTooltipOut(tooltipElement, callback = null) {
        if (!tooltipElement) return null;

        // Si el elemento ya no está en el DOM, ejecutar callback y retornar
        if (!tooltipElement.parentNode) {
            if (callback) callback();
            return null;
        }

        // Remover clase visible inmediatamente
        tooltipElement.classList.remove('visible');

        const animation = anime({
            targets: tooltipElement,
            opacity: [1, 0],
            scale: [1, 0.95],
            duration: 150,
            easing: 'easeInExpo',
            complete: () => {
                // Asegurar que el elemento se elimine del DOM
                if (tooltipElement && tooltipElement.parentNode) {
                    try {
                        tooltipElement.parentNode.removeChild(tooltipElement);
                    } catch (e) {
                        // Elemento ya fue eliminado, ignorar error
                        console.debug('[AnimeUtils] Tooltip ya eliminado');
                    }
                }
                if (callback) callback();
            }
        });

        return animation;
    }

    /**
     * Anima el loader de código con timeline coordinado
     * @param {HTMLElement} codeContainer - Contenedor de código
     * @param {HTMLElement} messageEl - Elemento del mensaje
     * @param {Array} codeLines - Array de objetos {num, code}
     * @param {Array} messages - Array de mensajes
     * @param {Function} createLineElement - Función para crear elementos de línea
     * @returns {Object} Timeline de anime.js
     */
    function animateCodeLoader(codeContainer, messageEl, codeLines, messages, createLineElement) {
        if (!codeContainer || !messageEl) return null;

        const timeline = anime.timeline({
            easing: 'easeOutExpo',
            autoplay: true
        });

        // Animar líneas de código con stagger
        codeLines.forEach((line, index) => {
            const lineEl = createLineElement ? createLineElement(line, index) : null;
            if (!lineEl) return;

            codeContainer.appendChild(lineEl);

            timeline.add({
                targets: lineEl,
                opacity: [0, 1],
                translateY: [-10, 0],
                duration: 300,
                delay: index * 150,
                begin: () => {
                    lineEl.classList.add('visible');
                }
            });
        });

        // Animar mensajes secuencialmente
        messages.forEach((message, index) => {
            timeline.add({
                targets: messageEl,
                opacity: [0, 1, 1, 0],
                duration: 500,
                delay: index * 250,
                update: (anim) => {
                    if (anim.progress < 50 && messageEl) {
                        messageEl.textContent = message;
                    }
                }
            });
        });

        return timeline;
    }

    /**
     * Anima la transición del timeline slider
     * @param {number} value - Valor del slider (0-23)
     * @param {Object} elements - Objeto con elementos {hourLabel, progressBar, forecastItems, labels}
     * @returns {Object} Timeline de anime.js
     */
    function animateTimelineUpdate(value, elements) {
        const { hourLabel, progressBar, forecastItems, labels } = elements;
        if (!hourLabel || !progressBar) return null;

        const progress = (value / 23) * 100;
        const currentProgress = parseFloat(progressBar.style.width) || 0;

        const timeline = anime.timeline({
            easing: 'easeOutExpo',
            duration: 300,
            autoplay: true
        });

        // Actualizar barra de progreso
        timeline.add({
            targets: progressBar,
            width: [`${currentProgress}%`, `${progress}%`],
            duration: 300,
            easing: 'easeOutExpo'
        });

        // Actualizar label de hora con fade
        timeline.add({
            targets: hourLabel,
            opacity: [1, 0],
            duration: 100,
            complete: () => {
                if (hourLabel) {
                    hourLabel.textContent = value == 0 ? 'Ahora' : `+${value}h`;
                }
            }
        }, '-=100');

        timeline.add({
            targets: hourLabel,
            opacity: [0, 1],
            duration: 200
        });

        // Actualizar items de forecast con stagger
        if (forecastItems && forecastItems.length > 0) {
            forecastItems.forEach((item, index) => {
                const itemHour = parseInt(item.dataset.hour) || 0;
                const isActive = itemHour == value;

                timeline.add({
                    targets: item,
                    scale: isActive ? [1, 1.05, 1] : [1.05, 1],
                    opacity: isActive ? [0.7, 1] : [1, 0.7],
                    duration: 200,
                    delay: index * 20,
                    begin: () => {
                        item.classList.toggle('active', isActive);
                    }
                }, '-=200');
            });
        }

        // Actualizar labels de timeline
        if (labels && labels.length > 0) {
            labels.forEach((label, i) => {
                const thresholds = [0, 6, 12, 23];
                const isActive = value >= thresholds[i] && (i === 3 || value < thresholds[i + 1]);

                timeline.add({
                    targets: label,
                    opacity: isActive ? [0.5, 1] : [1, 0.5],
                    scale: isActive ? [1, 1.1, 1] : [1.1, 1],
                    duration: 200,
                    delay: i * 30,
                    begin: () => {
                        label.classList.toggle('active', isActive);
                    }
                }, '-=150');
            });
        }

        return timeline;
    }

    /**
     * Anima el cambio de ubicación con fade coordinado
     * @param {HTMLElement} appElement - Elemento principal de la app
     * @param {Function} callback - Callback a ejecutar durante el fade out
     * @returns {Object} Timeline de anime.js
     */
    function animateLocationChange(appElement, callback) {
        if (!appElement) return null;

        const timeline = anime.timeline({
            easing: 'easeInOutExpo',
            duration: 300,
            autoplay: true
        });

        // Fade out
        timeline.add({
            targets: appElement,
            opacity: [1, 0],
            duration: 300,
            easing: 'easeInExpo'
        });

        // Ejecutar callback (cargar datos)
        timeline.add({
            duration: 0,
            complete: () => {
                if (callback) callback();
            }
        });

        // Fade in
        timeline.add({
            targets: appElement,
            opacity: [0, 1],
            duration: 300,
            easing: 'easeOutExpo'
        });

        return timeline;
    }

    /**
     * Anima el gauge de riesgo y sus barras
     * @param {number} riskScore - Score de riesgo (0-100) para el gauge
     * @param {Array} riskFactors - Array de factores {name, value}
     * @param {Object} options - Opciones {gaugeSelector, numberSelector, barSelector, originalScore}
     * @returns {Object} Timeline de anime.js
     */
    function animateRiskGauge(riskScore, riskFactors, options = {}) {
        const {
            gaugeSelector = '.risk-score-circle',
            numberSelector = '.risk-score-number',
            barSelector = '.risk-factor-fill',
            originalScore = null // Score original (0-5) para mostrar
        } = options;

        const gaugeCircle = document.querySelector(gaugeSelector);
        const numberEl = document.querySelector(numberSelector);

        if (!gaugeCircle) return null;

        const timeline = anime.timeline({
            easing: 'easeOutExpo',
            duration: 1000,
            autoplay: true
        });

        // Calcular offset del gauge circular
        // El radio del círculo SVG es 85 (según dashboard.html línea 5420)
        const radius = 85;
        const circumference = 2 * Math.PI * radius;
        // riskScore viene como 0-100 (porcentaje), calcular offset correctamente
        const offset = circumference - (riskScore / 100) * circumference;

        // Obtener el offset inicial del gauge (si existe)
        const currentOffset = gaugeCircle.getAttribute('stroke-dashoffset');
        const initialOffset = currentOffset ? parseFloat(currentOffset) : circumference;

        // Animar gauge circular desde su posición actual hasta el offset calculado
        timeline.add({
            targets: gaugeCircle,
            strokeDashoffset: [initialOffset, offset],
            duration: 1000,
            easing: 'easeOutExpo'
        });

        // Animar número del score
        if (numberEl) {
            // Usar el score original si está disponible, sino convertir de 0-100 a 0-5
            const scoreToShow = originalScore !== null ? originalScore : (riskScore / 100) * 5;
            timeline.add({
                targets: numberEl,
                scale: [0, 1.2, 1],
                opacity: [0, 1],
                duration: 600,
                delay: 200,
                update: (anim) => {
                    if (numberEl && anim.progress < 50) {
                        // Mostrar con 1 decimal (ej: 4.6 en lugar de 46)
                        numberEl.textContent = parseFloat(scoreToShow).toFixed(1);
                    }
                }
            }, '-=800');
        }

        // Animar barras de factores con stagger
        if (riskFactors && riskFactors.length > 0) {
            riskFactors.forEach((factor, index) => {
                const barElement = document.querySelector(
                    `[data-risk-factor="${factor.name}"] ${barSelector}`
                ) || document.querySelectorAll(barSelector)[index];

                if (barElement) {
                    timeline.add({
                        targets: barElement,
                        width: ['0%', `${factor.value}%`],
                        duration: 500,
                        delay: index * 100,
                        easing: 'easeOutExpo'
                    }, '-=400');
                }
            });
        }

        return timeline;
    }

    /**
     * Mejora la transición de tema con animaciones coordinadas
     * @param {boolean} isLight - Si el tema es light
     * @param {Object} options - Opciones {toggleSelector, cardSelector}
     * @returns {Object} Timeline de anime.js
     */
    function enhanceThemeTransition(isLight, options = {}) {
        const {
            toggleSelector = '.theme-toggle svg',
            cardSelector = '.card'
        } = options;

        const toggleIcon = document.querySelector(toggleSelector);
        const cards = document.querySelectorAll(cardSelector);

        const timeline = anime.timeline({
            easing: 'easeInOutExpo',
            duration: 500,
            autoplay: true
        });

        // Animar iconos del toggle
        if (toggleIcon) {
            timeline.add({
                targets: toggleIcon,
                rotate: [0, 180],
                scale: [1, 1.2, 1],
                duration: 400,
                easing: 'easeOutExpo'
            });
        }

        // Animar cards con stagger ligero
        if (cards && cards.length > 0) {
            timeline.add({
                targets: cards,
                opacity: [1, 0.7, 1],
                duration: 300,
                delay: anime.stagger(30),
                easing: 'easeInOutExpo'
            }, '-=200');
        }

        return timeline;
    }

    /**
     * Utilidades de fade reutilizables
     */
    const FadeUtils = {
        /**
         * Fade in genérico
         * @param {HTMLElement|NodeList|Array} element - Elemento(s) a animar
         * @param {number} duration - Duración en ms
         * @param {number} delay - Delay en ms
         * @returns {Object} Animación de anime.js
         */
        fadeIn(element, duration = 300, delay = 0) {
            if (!element) return null;

            return anime({
                targets: element,
                opacity: [0, 1],
                translateY: [20, 0],
                duration,
                delay,
                easing: 'easeOutExpo'
            });
        },

        /**
         * Fade out genérico
         * @param {HTMLElement|NodeList|Array} element - Elemento(s) a animar
         * @param {number} duration - Duración en ms
         * @param {Function} callback - Callback opcional
         * @returns {Object} Animación de anime.js
         */
        fadeOut(element, duration = 200, callback = null) {
            if (!element) return null;

            return anime({
                targets: element,
                opacity: [1, 0],
                translateY: [0, -20],
                duration,
                easing: 'easeInExpo',
                complete: callback
            });
        },

        /**
         * Fade in múltiples elementos con stagger
         * @param {NodeList|Array} elements - Elementos a animar
         * @param {number} duration - Duración en ms
         * @param {number} stagger - Delay entre elementos en ms
         * @returns {Object} Animación de anime.js
         */
        fadeInStagger(elements, duration = 300, stagger = 50) {
            if (!elements || elements.length === 0) return null;

            return anime({
                targets: elements,
                opacity: [0, 1],
                translateY: [20, 0],
                duration,
                delay: anime.stagger(stagger),
                easing: 'easeOutExpo'
            });
        }
    };

    // Exportar al objeto global window
    window.AnimeUtils = {
        animateAlertIn,
        animateAlertOut,
        animateTooltipIn,
        animateTooltipOut,
        animateCodeLoader,
        animateTimelineUpdate,
        animateLocationChange,
        animateRiskGauge,
        enhanceThemeTransition,
        FadeUtils,
        // Exportar instancia de anime para uso avanzado
        anime: anime
    };

    // Log de inicialización
    console.log('[AnimeUtils] Utilidades de animación cargadas correctamente');

})(window);

