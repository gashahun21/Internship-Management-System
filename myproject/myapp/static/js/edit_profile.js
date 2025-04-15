// static/js/image_preview.js
document.addEventListener('DOMContentLoaded', function() {
    // Select the file input and the preview image elements
    // *** IMPORTANT: Ensure the ID 'id_profile_image' matches the actual ID Django assigns to your form's profile_image field ***
    // Inspect your HTML source if needed. Default is usually 'id_<fieldname>'
    const imageInput = document.getElementById('id_profile_image');
    const imagePreview = document.getElementById('imagePreview');
    const currentImagePreview = document.getElementById('imagePreviewCurrent');

    if (imageInput && imagePreview) {
        imageInput.addEventListener('change', function(event) {
            const file = event.target.files[0];

            if (file) {
                // Check if the file is an image
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();

                    reader.onload = function(e) {
                        // Set the src of the preview image
                        imagePreview.src = e.target.result;
                        // Display the preview image
                        imagePreview.style.display = 'block';
                        // Optionally hide the 'current' image preview if one exists
                        if (currentImagePreview) {
                            currentImagePreview.style.display = 'none';
                        }
                    }
                    // Read the file as a Data URL
                    reader.readAsDataURL(file);
                } else {
                    // Handle non-image file selection (optional)
                    alert("Please select a valid image file.");
                    // Clear the preview and input
                    imagePreview.src = '#';
                    imagePreview.style.display = 'none';
                    // Show current image again if it was hidden
                     if (currentImagePreview) {
                            currentImagePreview.style.display = 'block';
                     }
                    imageInput.value = ''; // Clear the file input
                }
            } else {
                // No file selected, clear preview
                imagePreview.src = '#';
                imagePreview.style.display = 'none';
                 // Show current image again if it was hidden
                 if (currentImagePreview) {
                     currentImagePreview.style.display = 'block';
                 }
            }
        });
    } else {
        if (!imageInput) console.error("Image input element not found. Check the ID.");
        if (!imagePreview) console.error("Image preview element not found. Check the ID.");
    }
});