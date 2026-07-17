# StegaVault Software Requirements Specification (SRS)

## Abstract
StegaVault is a full-stack web application for image steganography, watermarking, and tamper detection. It enables users to securely hide text or images inside a cover image, add visible and invisible watermarks, compute cryptographic image hashes, and compare images for tampering. The backend is implemented in Python using only standard library HTTP server components plus selected image and crypto libraries, while the frontend is a responsive single-page application written in vanilla HTML, CSS, and JavaScript.

## Table of Contents
1. Introduction
   - Background of the Project
   - Problem Definition
   - Motivation for the Project
   - Objectives and Scope of the Project
2. Literature Review
   - Research and existing solutions in the domain
   - Comparative analysis of existing platforms
   - How the project differs from existing work
3. System Analysis
   - Functional Requirements
   - Non-Functional Requirements
4. Technology Stack
   - Languages, frameworks, and tools used
   - Explanation of why these tools were selected
5. System Design
   - Use Case Diagram
   - Architecture Diagram
   - Database Design
   - UI/UX Design
   - Modules/Components Overview
   - Features Developed
6. Testing
   - Types of testing performed
   - Tools used for testing
   - Test cases and results
7. Results
   - Screenshots of the final product
   - Explanation of functionality achieved
   - Performance benchmarks
8. Challenges Faced
   - Development challenges encountered
   - Solutions or workarounds used
9. Conclusion and Future Scope
   - Summary of project achievements
   - Potential areas for improvement or future features
References
Appendices
Problem statement approval form

## 1. Introduction

### Background of the Project
Digital images are frequently used to store or transmit sensitive information, but standard image formats alone do not provide confidentiality or authenticity guarantees. StegaVault addresses this by combining steganography, watermarking, and tamper detection in one browser-accessible platform.

### Problem Definition
Users need an easy and secure way to:
- hide secret text inside a cover image,
- conceal an entire secret image in another image,
- protect hidden payloads with authenticated encryption,
- embed invisible and visible watermarks to assert ownership,
- detect whether an image has been altered after distribution.

Existing tools are often fragmented or require desktop installation, and they may not provide both hiding and forensic verification capabilities in one package.

### Motivation for the Project
The motivation is to create a unified, lightweight, local web application that demonstrates practical information hiding and forensic techniques without complex dependencies. StegaVault is intended for users interested in privacy, copyright protection, and image integrity verification.

### Objectives and Scope of the Project
Objectives:
- Implement text and image steganography using least significant bit (LSB) embedding.
- Support optional AES-256-GCM encryption for hidden payloads.
- Implement invisible watermarking using DCT coefficient modification.
- Support visible text and visible image watermarks.
- Provide tamper detection using SHA-256 hashing and pixel-diff heatmaps.
- Serve functionality via a lightweight browser dashboard and API.

Scope:
- Browser-based single-page application with no external frontend frameworks.
- Python backend using only standard library HTTP server plus selected image/crypto libraries.
- Local runtime storage in `uploads/`, `outputs/`, and `logs/`.
- No user authentication or persistent user database.

## 2. Literature Review

### Research and Existing Solutions in the Domain
Relevant techniques include:
- LSB steganography for hiding payloads in pixel bitplanes.
- DCT-based invisible watermarking for frequency-domain data embedding.
- AES-256-GCM for authenticated symmetric encryption.
- SHA-256 hashing for tamper detection.
- Pixel difference heatmaps for visual tamper localization.

Academic and prototype tools usually focus on either steganography, watermarking, or hashing, but seldom combine all three.

### Comparative Analysis of Existing Platforms
Existing systems typically fall into these categories:
- desktop steganography apps with limited encryption or watermarking,
- online demos that only provide basic hiding techniques,
- academic examples that lack a user-friendly interface.

StegaVault stands out by integrating:
- text and image LSB steganography,
- AES-256-GCM protected payloads,
- invisible DCT watermarking,
- visible watermark overlays,
- tamper detection and heatmap generation,
- browser-based UI with API docs built in.

### How the Project Differs from Existing Work
StegaVault builds on established steganography and watermarking methods and combines them in a single web-accessible application. It extends LSB payload hiding with authenticated encryption, adds blind DCT watermark extraction, and provides forensic tools that many comparable apps do not include.

## 3. System Analysis

### Functional Requirements
1. Users can upload a cover image and embed secret text using LSB steganography.
2. Users can optionally encrypt hidden text with AES-256-GCM before embedding.
3. Users can extract hidden text from a stego image using the same password if encryption was used.
4. Users can upload a secret image and hide it inside a cover image using LSB steganography.
5. Users can extract a hidden image from a stego image, with optional decryption.
6. Users can embed an invisible watermark using DCT coefficient modification.
7. Users can extract an invisible DCT watermark from a watermarked image.
8. Users can add a visible text watermark to an image with configurable opacity, position, and font size.
9. Users can add a visible image watermark/logo overlay to an image with configurable opacity, position, and scale.
10. Users can compute a SHA-256 hash for an image.
11. Users can verify image integrity by comparing a hash against an image.
12. Users can generate a tamper-detection heatmap comparing an original image to a suspect image.
13. Users can perform LSB noise analysis to detect suspiciously uniform LSB bit distributions.
14. The frontend displays operation history and algorithm reference data.
15. The backend serves a single-page app, static resources, API endpoints, and Swagger documentation.

### Non-Functional Requirements
- Run locally using Python 3.9 or later.
- Provide a responsive UI on modern browsers.
- Return JSON responses and support CORS.
- Preserve lossless PNG output for steganographic results.
- Avoid large frontend frameworks.
- Handle invalid images and application errors gracefully.
- Provide upload previews, progress indicators, and toast notifications.

## 4. Technology Stack

### Languages, Frameworks, and Tools
- Python 3.9+ for the backend.
- HTML5, CSS3, and vanilla JavaScript for the frontend.
- Pillow for image loading, conversion, drawing, and PNG output.
- NumPy for pixel-array manipulation and numerical operations.
- SciPy for DCT and IDCT transforms.
- cryptography for AES-256-GCM encryption and PBKDF2.
- OpenCV (`opencv-python-headless`) for broader image support.
- Python standard library `http.server` for request handling.

### Explanation of Tool Selection
- Standard library HTTP server keeps the backend lightweight and dependency-minimal.
- Pillow is the core image-processing library for the project.
- NumPy enables efficient bitwise and array operations required by steganography and tamper detection.
- SciPy supports the DCT-based invisible watermark algorithm.
- cryptography enables modern authenticated encryption.
- Vanilla JS avoids frontend build tooling and keeps the UI simple.

## 5. System Design

### Use Case Diagram
Primary actor: End user.
Use cases:
- Hide text inside an image.
- Extract text from a stego image.
- Hide an image inside another image.
- Extract a hidden image.
- Embed invisible watermark.
- Extract invisible watermark.
- Add visible text watermark.
- Add visible image watermark.
- Compute an image hash.
- Verify image integrity.
- Generate a tamper detection heatmap.
- Analyze LSB noise.
- View operation history.

### Architecture Diagram
The architecture consists of:
- Frontend: `frontend/index.html`, `frontend/css/style.css`, `frontend/js/app.js`
- Backend server: `server.py`
- Service modules: `backend/services/*.py`
- Utility modules: `backend/utils/*.py`
- Runtime directories: `uploads/`, `outputs/`, `logs/`

Requests from the browser are routed through `server.py`, which calls service functions and returns JSON responses.

### Database Design
No database is used. The system uses file-based storage for uploads and outputs, and operation history is stored in-memory and cleared on restart.

### UI/UX Design
The UI is a single-page dashboard with a sidebar configuration menu. It includes:
- drag-and-drop uploads,
- file previews,
- a capacity bar for text embedding,
- password show/hide toggles,
- toast notifications,
- light/dark mode,
- an algorithms reference panel.

### Modules/Components Overview
- `server.py`: routes requests, parses multipart forms, serves frontend resources, and exposes `/docs`.
- `backend/services/lsb_steganography.py`: encodes/decodes text and image payloads into LSB bits, handles capacity and optional encryption.
- `backend/services/watermarking.py`: invisible DCT watermark embed/extract; visible text and image watermark rendering.
- `backend/services/tamper_detection.py`: SHA-256 hash comparison, pixel-difference heatmap generation, and LSB noise analysis.
- `backend/utils/encryption.py`: PBKDF2 key derivation and AES-256-GCM encryption/decryption.
- `backend/utils/hashing.py`: image hash computation and comparison logic.
- `backend/utils/file_utils.py`: image validation and thumbnail generation.
- `backend/utils/logger.py`: in-memory audit log.
- `frontend/js/app.js`: UI management, file handling, API calls, and notification rendering.

### Features Developed
- LSB text embedding with optional AES-256-GCM encryption.
- LSB image hiding with automatic secret image resizing.
- Invisible DCT watermark embedding and blind extraction.
- Visible text watermark rendering.
- Visible image watermark overlay.
- SHA-256 image hash generation and verification.
- Tamper-detection heatmap generation.
- LSB noise analysis.
- Operation history and algorithm reference panels.

## 6. Testing

### Types of Testing Performed
- Functional testing of the frontend workflows.
- Integration testing of frontend-to-backend requests.
- System testing of full steganography and watermarking flows.
- Error handling validation for invalid inputs and wrong passwords.

### Tools Used for Testing
- Manual browser testing.
- Manual API endpoint validation.
- No automated test framework is included.

### Test Cases and Results
1. Hide text in image
   - Result: passed.
2. Extract text from stego image
   - Result: passed.
3. Hide image in image
   - Result: passed.
4. Extract hidden image
   - Result: passed.
5. Embed and extract DCT watermark
   - Result: passed.
6. Compute and verify image hash
   - Result: passed.
7. Generate tamper heatmap
   - Result: passed.
8. LSB noise analysis
   - Result: passed.

## 7. Results

### Functionality Achieved
StegaVault successfully delivers a browser-based environment for image-based steganography, watermarking, and tamper detection. The implemented features include text hiding, image hiding, invisible and visible watermarking, hash verification, and tamper heatmaps.

### Performance Benchmarks
- LSB steganography operations complete quickly for images under 20 MB.
- DCT watermark embedding/extraction is acceptable for moderate image sizes.
- SHA-256 hashing and LSB noise analysis are near instantaneous.

### Screenshots of the Final Product
Screenshot files are not included in the repository. The frontend layout is described by `frontend/index.html` and `frontend/css/style.css`.

## 8. Challenges Faced

### Development Challenges
- Implementing multipart/form-data parsing using Python standard library tools.
- Designing DCT watermark embedding and blind extraction.
- Calculating payload capacity and resizing secret images safely.
- Supporting optional AES encryption while preserving LSB embedding.

### Solutions or Workarounds Used
- Used Python's `email` parser for multipart parsing.
- Used SciPy DCT/IDCT with coefficient parity quantisation.
- Added length headers for payload framing.
- Used AES-256-GCM with PBKDF2 for encryption.

## 9. Conclusion and Future Scope

### Summary of Project Achievements
StegaVault provides a complete web-based platform for secure image steganography, watermarking, and tamper detection. It delivers visual and invisible protections, optional encryption, and integrity verification in a lightweight architecture.

### Potential Areas for Improvement or Future Features
- Add user accounts and persistent project storage.
- Add automated test coverage.
- Support batch image processing.
- Add additional steganography methods.
- Improve mobile responsiveness and image cropping.

## References
- Pillow library documentation
- NumPy and SciPy documentation
- cryptography library documentation
- SHA-256 integrity verification theory
- LSB and DCT watermarking research literature

## Appendices
### Appendix A — API Endpoints
- `GET /api/health`
- `GET /api/history`
- `DELETE /api/history`
- `GET /api/algorithms`
- `POST /api/stego/encode-text`
- `POST /api/stego/decode-text`
- `POST /api/stego/encode-image`
- `POST /api/stego/decode-image`
- `POST /api/watermark/embed-dct`
- `POST /api/watermark/extract-dct`
- `POST /api/watermark/visible-text`
- `POST /api/watermark/visible-image`
- `POST /api/tamper/get-hash`
- `POST /api/tamper/verify-hash`
- `POST /api/tamper/diff-heatmap`
- `POST /api/tamper/lsb-noise`

### Appendix B — Runtime File Structure
- `uploads/` — temporary uploads
- `outputs/` — generated output files
- `logs/` — operation logs

### Appendix C — Problem Statement Approval Form
Project title: StegaVault
Description: Image steganography, watermarking, and tamper detection platform.
Prepared by: ____________________
Approved by: ____________________
Date: ____________________

