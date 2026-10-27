/* Keyboard navigation for the comboboxes, per the ARIA 1.2 combobox pattern.
 * Adapted from the wtforms-htmx-components example. Handlers sit on the
 * document, so they keep working after htmx swaps. */
(function () {
    const OPTION = '.combobox > [role="listbox"] > [role="option"]';

    function options(combobox) {
        return Array.from(combobox.querySelectorAll(OPTION));
    }

    function input(combobox) {
        return combobox.querySelector('[role="combobox"]');
    }

    function close(combobox) {
        combobox.dataset.comboboxClosed = "true";
    }

    function open(combobox) {
        delete combobox.dataset.comboboxClosed;
    }

    document.addEventListener("keydown", function (e) {
        const combobox = e.target.closest?.(".combobox");
        if (!combobox) return;

        if (e.target.matches('[role="combobox"]')) {
            const buttons = options(combobox);

            if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                open(combobox);
                if (!buttons.length) return;
                e.preventDefault();
                buttons[e.key === "ArrowDown" ? 0 : buttons.length - 1].focus();
                return;
            }

            if (e.key === "Backspace" && e.target.value === "") {
                const removes = combobox.querySelectorAll(".combobox-remove");
                if (!removes.length) return;
                e.preventDefault();
                removes[removes.length - 1].click();
                return;
            }

            // Without this, Enter clicks the first button of the form,
            // which can be the remove button of a chip.
            if (e.key === "Enter") {
                e.preventDefault();
                buttons[0]?.click();
                return;
            }
        }

        if (e.target.matches(OPTION)) {
            const buttons = options(combobox);
            const index = buttons.indexOf(e.target);
            const moves = {
                ArrowDown: buttons[(index + 1) % buttons.length],
                ArrowUp: index === 0 ? input(combobox) : buttons[index - 1],
                Home: buttons[0],
                End: buttons[buttons.length - 1],
            };
            if (e.key in moves) {
                e.preventDefault();
                moves[e.key]?.focus();
                return;
            }
        }

        if (e.key === "Escape") {
            e.preventDefault();
            // Focus before closing, so the focus events cannot reopen it.
            input(combobox)?.focus();
            close(combobox);
        }
    });

    document.addEventListener("input", function (e) {
        const combobox = e.target.closest?.(".combobox");
        if (combobox) open(combobox);
    });

    // The chips and the input look like a single field: a click on a chip
    // or around them focuses the input.
    document.addEventListener("click", function (e) {
        const field = e.target.closest?.(".combobox-field");
        if (!field || e.target.closest("button, input")) return;
        input(field.closest(".combobox"))?.focus();
    });

    document.addEventListener("focusout", function (e) {
        const combobox = e.target.closest?.(".combobox");
        if (!combobox) return;
        if (e.relatedTarget?.closest?.(".combobox") === combobox) return;
        // Safari does not focus a clicked button: keep the options for the click.
        if (combobox.matches(":hover")) return;
        close(combobox);
    });

    document.addEventListener("mouseover", function (e) {
        const option = e.target.closest?.(OPTION);
        if (!option || !document.activeElement?.matches(OPTION)) return;
        if (document.activeElement !== option) {
            option.focus({ preventScroll: true });
        }
    });

    // Browsers ignore autofocus on swapped content: apply it after a pick.
    if (!window.htmx) return;
    htmx.onLoad(function (root) {
        const target = root.matches?.('[role="combobox"][autofocus]')
            ? root
            : root.querySelector?.('[role="combobox"][autofocus]');
        if (!target) return;
        const combobox = target.closest(".combobox");
        if (combobox) open(combobox);
        target.focus();
    });
})();
