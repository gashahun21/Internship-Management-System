// Example main.js content for floating labels
document.addEventListener('DOMContentLoaded', () => {
    const inputs = document.querySelectorAll(".input");

    function addFocusClass() {
        let parent = this.parentNode.parentNode; // Get .input-div
        parent.classList.add("focus");
    }

    function removeFocusClass() {
        let parent = this.parentNode.parentNode; // Get .input-div
        if (this.value == "") { // Only remove focus class if input is empty
            parent.classList.remove("focus");
        }
    }

    function checkValueOnLoad() {
        if (this.value !== "") {
             let parent = this.parentNode.parentNode;
             parent.classList.add("focus"); // Add focus class if pre-filled
        }
    }

    inputs.forEach(input => {
        input.addEventListener("focus", addFocusClass);
        input.addEventListener("blur", removeFocusClass);
        checkValueOnLoad.call(input); // Check value when page loads (e.g., browser autofill)
    });
});