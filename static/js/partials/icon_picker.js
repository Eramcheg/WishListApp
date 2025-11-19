const LUCIDE_ICONS = [
  "heart", "star", "gift", "bookmark", "shopping-bag",
  "user", "users", "home", "calendar", "list",
  "music", "camera", "film", "gamepad-2", "plane",
  "book", "coffee", "pizza", "smile", "sun",
];

function initIconPickers() {
  const pickers = document.querySelectorAll("[data-icon-picker]");
  if (!pickers.length) return;

  pickers.forEach(picker => {
    const input = picker.querySelector("[data-icon-input]");
    const openBtn = picker.querySelector("[data-icon-open]");
    const preview = picker.querySelector("[data-icon-preview]");
    const modalBackdrop = picker.querySelector("[data-icon-modal-backdrop]");
    const closeBtn = picker.querySelector("[data-icon-close]");
    const searchInput = picker.querySelector("[data-icon-search]");
    const grid = picker.querySelector("[data-icon-grid]");

    let currentValue = input.value || "";

    // Рендер сетки иконок
    function renderIcons(filter = "") {
      grid.innerHTML = "";
      const icons = LUCIDE_ICONS.filter(name =>
        name.toLowerCase().includes(filter.toLowerCase())
      );
      icons.forEach(name => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = [
          "flex flex-col items-center justify-center gap-1 rounded-md border",
          "px-2 py-2 hover:bg-gray-50 text-xs",
          currentValue === name ? "border-indigo-500 ring-2 ring-indigo-300" : "border-gray-200"
        ].join(" ");
        btn.dataset.iconName = name;

        btn.innerHTML = `
          <span class="w-6 h-6 flex items-center justify-center">
            <i data-lucide="${name}"></i>
          </span>
          <span class="truncate w-full text-[10px]">${name}</span>
        `;
        btn.addEventListener("click", () => {
          currentValue = name;
          input.value = name;

          // обновляем превью
          preview.innerHTML = `<i data-lucide="${name}"></i>`;
          lucide.createIcons(preview);

          closeModal();
        });

        grid.appendChild(btn);
      });

      lucide.createIcons(grid);
    }

    function openModal() {
      modalBackdrop.classList.remove("hidden");
      renderIcons("");
      searchInput.value = "";
      searchInput.focus();
    }

    function closeModal() {
      modalBackdrop.classList.add("hidden");
    }

    openBtn.addEventListener("click", openModal);
    closeBtn.addEventListener("click", closeModal);
    modalBackdrop.addEventListener("click", (e) => {
      if (e.target === modalBackdrop) closeModal();
    });

    searchInput.addEventListener("input", (e) => {
      renderIcons(e.target.value);
    });

    // Первоначальное превью
    if (currentValue) {
      preview.innerHTML = `<i data-lucide="${currentValue}"></i>`;
      lucide.createIcons(preview);
    } else {
      lucide.createIcons(preview);
    }
  });
}

// Инициализация после загрузки страницы
document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) {
    initIconPickers();
  } else {
    console.warn("Lucide не найден. Подключи lucide.js перед icon-picker.js");
  }
});
