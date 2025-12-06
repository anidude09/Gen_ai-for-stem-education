/**
 * ImageUploader.jsx
 *
 * This component provides a file input to upload an image.
 * - When a user selects an image, it creates a temporary object URL
 * - Updates the parent component with the new image URL
 * - Resets any existing detection/overlay states to start fresh
 */
function ImageUploader({ setImageUrl, resetStates }) {
  const handleUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const url = URL.createObjectURL(file);
    setImageUrl(url);
    resetStates();
  };

  return (
    <label className="upload-btn-wrapper">
        <span className="upload-btn-text">Upload Image</span>
        <input
            type="file"
            accept="image/*"
            onChange={handleUpload}
            className="file-input-hidden"
        />
    </label>
  );
}

export default ImageUploader;
