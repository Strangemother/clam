"use strict";

const config = window.promptRunnerConfig;

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    let body;
    try {
        body = await response.json();
    } catch (error) {
        throw new Error(`Server returned invalid JSON: ${error.message}`);
    }
    if (!response.ok) {
        throw new Error(body.error?.message || "The request failed.");
    }
    return body;
}

Vue.createApp({
    delimiters: ["[[", "]]"],

    data() {
        return {
            config,
            prompts: config.prompts,
            selectedPrompt: "",
            prompt: null,
            promptState: "",
            selectedExample: "",
            userInput: "",
            backend: "",
            models: [],
            selectedModel: "",
            loadingPrompt: false,
            loadingModels: false,
            running: false,
            error: "",
            modelStatus: "",
            resultText: "",
            activeTab: "runner",
            draggingImage: false,
            imageFile: null,
            imagePreview: "",
            imageStatus: "",
            imageLoadError: false,
            resultData: null,
            copyStatus: "",
            theme: (
                localStorage.getItem("prompt-runner-theme")
                || (
                    window.matchMedia(
                        "(prefers-color-scheme: dark)",
                    ).matches
                        ? "dark"
                        : "light"
                )
            ),
            promptRequestId: 0,
        };
    },

    computed: {
        selectedExampleData() {
            if (!this.prompt || this.selectedExample === "") {
                return null;
            }
            return this.prompt.examples.find(
                example => (
                    String(example.index) === this.selectedExample
                ),
            ) || null;
        },

        imageDisplayUrl() {
            if (
                this.backend !== "local"
                || !this.selectedExampleData
                || !this.selectedExampleData.is_image
            ) {
                return "";
            }
            if (this.imagePreview) {
                return this.imagePreview;
            }
            return (
                `${this.config.image_url}/`
                + `${encodeURIComponent(this.selectedPrompt)}/`
                + this.selectedExampleData.index
            );
        },

        resultBoxes() {
            const answers = this.resultData?.answers;
            if (!answers || typeof answers !== "object") {
                return [];
            }

            const boxes = [];
            const colors = ["#ff4d4d", "#27a5ff", "#ffc247", "#51c878"];
            const addBox = (value, label, index, color) => {
                if (!value || typeof value !== "object") {
                    return;
                }
                const {top, bottom, left, right} = value;
                if (
                    ![top, bottom, left, right].every(
                        coordinate => (
                            typeof coordinate === "number"
                            && Number.isFinite(coordinate)
                            && coordinate >= 0
                            && coordinate <= 1
                        ),
                    )
                    || bottom < top
                    || right < left
                ) {
                    return;
                }
                boxes.push({
                    label: index === null
                        ? label
                        : `${label} ${index + 1}`,
                    top,
                    bottom,
                    left,
                    right,
                    color,
                });
            };

            for (const [name, answer] of Object.entries(answers)) {
                if (!answer || typeof answer !== "object") {
                    continue;
                }
                const color = colors[boxes.length % colors.length];
                addBox(answer.box, name, null, color);
                if (Array.isArray(answer.boxes)) {
                    answer.boxes.forEach((box, index) => {
                        addBox(box.box || box, name, index, color);
                    });
                }
            }
            return boxes;
        },

        compatibilityMessage() {
            if (!this.prompt || this.backend !== "lm_studio") {
                return "";
            }
            if (!this.prompt.lm_studio_questions_supported) {
                return (
                    "LM Studio supports only noul, choice, and score "
                    + "questions in this prompt."
                );
            }
            if (
                this.selectedExampleData
                && this.selectedExampleData.is_image
                && !this.userInput.trim()
            ) {
                return (
                    "LM Studio cannot process images. Enter a text message "
                    + "to use instead of this image example."
                );
            }
            return "";
        },

        canRun() {
            if (!this.prompt || !this.backend) {
                return false;
            }
            if (!this.userInput.trim() && !this.selectedExampleData) {
                return false;
            }
            if (this.backend === "lm_studio") {
                return Boolean(
                    this.selectedModel && !this.compatibilityMessage,
                );
            }
            return true;
        },
    },

    watch: {
        selectedPrompt(name) {
            this.loadPrompt(name);
        },

        backend(value) {
            this.resultData = null;
            this.resultText = "";
            if (value === "lm_studio") {
                this.loadModels();
                this.imageFile = null;
                this.imageStatus = "";
            }
        },

        selectedExampleData(example) {
            this.imageLoadError = false;
            this.resultData = null;
            this.resultText = "";
            if (!example || !example.is_image) {
                this.imageFile = null;
                this.imageStatus = "";
            }
        },

        imageFile(file) {
            if (this.imagePreview) {
                URL.revokeObjectURL(this.imagePreview);
            }
            this.resultData = null;
            this.resultText = "";
            this.imagePreview = file ? URL.createObjectURL(file) : "";
            if (!file && this.$refs.imageFileInput) {
                this.$refs.imageFileInput.value = "";
            }
        },

        promptState() {
            this.resultData = null;
            this.resultText = "";
        },

        userInput() {
            this.resultData = null;
            this.resultText = "";
        },

        theme(value) {
            document.documentElement.dataset.theme = value;
            localStorage.setItem("prompt-runner-theme", value);
        },
    },

    mounted() {
        document.documentElement.dataset.theme = this.theme;
    },

    beforeUnmount() {
        if (this.imagePreview) {
            URL.revokeObjectURL(this.imagePreview);
        }
    },

    methods: {
        async loadPrompt(name) {
            const requestId = ++this.promptRequestId;
            this.prompt = null;
            this.promptState = "";
            this.selectedExample = "";
            this.userInput = "";
            this.imageFile = null;
            this.resultData = null;
            this.resultText = "";
            this.imageLoadError = false;
            this.error = "";
            if (!name) {
                return;
            }

            this.loadingPrompt = true;
            try {
                const url = (
                    this.config.prompt_url + encodeURIComponent(name)
                );
                const data = await fetchJson(url, {
                    headers: {"Accept": "application/json"},
                });
                if (requestId !== this.promptRequestId) {
                    return;
                }
                this.prompt = data;
                this.promptState = data.state;
            } catch (error) {
                if (requestId === this.promptRequestId) {
                    this.error = error.message;
                }
            } finally {
                if (requestId === this.promptRequestId) {
                    this.loadingPrompt = false;
                }
            }
        },

        async loadModels() {
            this.loadingModels = true;
            this.modelStatus = "";
            try {
                const data = await fetchJson(this.config.models_url, {
                    headers: {"Accept": "application/json"},
                });
                this.models = data.models;
                if (!this.models.includes(this.selectedModel)) {
                    this.selectedModel = "";
                }
                this.modelStatus = this.models.length
                    ? `Found ${this.models.length} loaded decision model(s).`
                    : "No loaded decision models were found.";
            } catch (error) {
                this.models = [];
                this.selectedModel = "";
                this.modelStatus = error.message;
            } finally {
                this.loadingModels = false;
            }
        },

        toggleTheme() {
            this.theme = this.theme === "dark" ? "light" : "dark";
        },

        acceptImage(file) {
            const supportedTypes = [
                "image/jpeg",
                "image/png",
                "image/webp",
            ];
            if (!supportedTypes.includes(file.type)) {
                this.imageStatus = "Choose a PNG, JPEG, or WebP image.";
                return;
            }
            if (file.size > 64 * 1024 * 1024) {
                this.imageStatus = "Image exceeds the 64 MiB limit.";
                return;
            }
            this.imageStatus = "";
            this.imageFile = file;
        },

        handleImageChange(event) {
            const [file] = event.target.files;
            if (file) {
                this.acceptImage(file);
            }
        },

        handleImageDrop(event) {
            this.draggingImage = false;
            const [file] = event.dataTransfer.files;
            if (file) {
                this.acceptImage(file);
            }
        },

        onImageLoad() {
            this.imageLoadError = false;
        },

        onImageError() {
            this.imageLoadError = true;
        },

        async runPrompt() {
            if (!this.canRun || this.running) {
                return;
            }
            this.running = true;
            this.error = "";
            this.resultData = null;
            this.resultText = "";

            const form = new FormData();
            form.append("prompt", this.selectedPrompt);
            form.append("backend", this.backend);
            form.append("model", this.selectedModel);
            form.append("example", this.selectedExample);
            form.append("prompt_state", this.promptState);
            form.append("user_prompt", this.userInput);
            if (this.imageFile) {
                form.append("image_override", this.imageFile);
            }

            try {
                const data = await fetchJson(this.config.run_url, {
                    method: "POST",
                    body: form,
                });
                this.resultData = data;
                this.resultText = JSON.stringify(data, null, 2);
            } catch (error) {
                this.error = error.message;
            } finally {
                this.running = false;
            }
        },

        async copyRequest() {
            const code = this.$refs.pythonRequest.textContent;
            try {
                await navigator.clipboard.writeText(code);
                this.copyStatus = "Copied.";
            } catch (error) {
                this.copyStatus = (
                    `Could not copy: ${error.message}. `
                    + "Select the code manually."
                );
            }
        },
    },
}).mount("#app");
