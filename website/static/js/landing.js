document.addEventListener('DOMContentLoaded', function() {
    // Auto-launch the "You're Early!" modal on page load
    const earlyModal = new bootstrap.Modal(document.getElementById('earlyModal'), {
        keyboard: false
    });
    earlyModal.show(); // Show the "You're Early!" modal

    // Get references to the forms and buttons
    const thropicForm = document.getElementById('thropicForm');
    const submitBtn = document.getElementById('submitBtn');
    const sentimentForm = document.getElementById('sentimentForm');
    const sentimentSubmitBtn = document.getElementById('sentimentSubmitBtn');
    const scrapeForm = document.getElementById('scrapeForm');
    const scrapeSubmitBtn = document.getElementById('scrapeSubmitBtn');
    const imageGenForm = document.getElementById('imageGenForm');
    const imageGenSubmitBtn = document.getElementById('imageGenSubmitBtn');
    const transcriptSubmitBtn = document.getElementById('transcriptSubmitBtn');
    const modalBody = document.getElementById('modalBody');
    const submissionModal = new bootstrap.Modal(document.getElementById('submissionModal'));

    // Create loading spinner HTML
    const spinnerHTML = `
        <div class="d-flex justify-content-center">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
        <p class="text-center">Processing, please wait...</p>
    `;

    // Format the AI response, handling code and text formatting
    function formatResponse(response) {
        console.log("Formatting AI response...");
        let formattedText = response.replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>');
        formattedText = formattedText.replace(/`([^`]+)`/g, '<code>$1</code>');
        formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formattedText = formattedText.replace(/\n/g, '<br>');
        return formattedText;
    }

    // Function to handle form submission and API request
    function submitForm(form, apiUrl) {
        const formData = new FormData(form);
        const prompt = formData.get('prompt'); // Extract the prompt field

        // Ensure the prompt is not empty
        if (!prompt || prompt.trim() === "") {
            modalBody.textContent = 'Prompt is required.';
            submissionModal.show();
            return;
        }

        const payload = { prompt: prompt };

        // Show the spinner in the modal and clear previous content
        modalBody.innerHTML = spinnerHTML;
        submissionModal.show();

        // Send the API request
        fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload) // Convert FormData to JSON format
        })
        .then(response => response.json())
        .then(data => {
            // Update modal content based on the API response
            if (data.error) {
                modalBody.textContent = JSON.stringify(data.error, null, 2);
            } else {
                // Check if it is an image generation request to display the image
                if (apiUrl === '/rag-api-image') {
                    modalBody.innerHTML = `<img src="${data.result}" alt="Generated Image" class="img-fluid"/>`;
                } else {
                    modalBody.innerHTML = formatResponse(data.message || data.result); // Display formatted result from the API
                }
            }
        })
        .catch(error => {
            modalBody.textContent = 'An error occurred while processing the request.';
        });
    }

    // Function to handle GET request for transcription
    function submitTranscriptRequest() {
        // Show the spinner in the modal and clear previous content
        modalBody.innerHTML = spinnerHTML;
        submissionModal.show();

        // Send the GET request to the transcription API
        fetch('/rag-api-transcript', {
            method: 'GET'
        })
        .then(response => response.json())
        .then(data => {
            // Update modal content based on the API response
            if (data.error) {
                modalBody.textContent = JSON.stringify(data.error, null, 2);
            } else {
                modalBody.innerHTML = formatResponse(data.result);
            }
        })
        .catch(error => {
            modalBody.textContent = 'An error occurred while processing the request.';
        });
    }

    // Event listener for thropicForm submit button
    submitBtn.addEventListener('click', function() {
        submitForm(thropicForm, '/rag-api');
    });

    // Event listener for sentimentForm submit button
    sentimentSubmitBtn.addEventListener('click', function() {
        submitForm(sentimentForm, '/rag-api-sentiment');
    });

    // Event listener for scrapeForm submit button
    scrapeSubmitBtn.addEventListener('click', function() {
        submitForm(scrapeForm, '/rag-api-webscrape');
    });

    // Event listener for imageGenForm submit button
    imageGenSubmitBtn.addEventListener('click', function() {
        submitForm(imageGenForm, '/rag-api-image');
    });

    // Event listener for transcriptForm submit button (GET request)
    transcriptSubmitBtn.addEventListener('click', function() {
        submitTranscriptRequest();
    });

    // Confirm submit functionality
    document.getElementById('confirmSubmit').addEventListener('click', function() {
        var form = document.querySelector('form');
        form.submit(); // Submit the form
    });

    // Dropdown functionality
    document.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', function() {
            var filename = this.getAttribute('data-filename');
            var downloadLink = document.getElementById('downloadLink');
            downloadLink.href = `/download_plate/${filename}`;
            var dropdownButton = document.getElementById('dropdownMenuButton');
            dropdownButton.textContent = this.textContent;
        });
    });

    // Check if an element is in the viewport
    function isElementInView(element) {
        var elementTop = $(element).offset().top;
        var elementBottom = elementTop + $(element).outerHeight();
        var viewportTop = $(window).scrollTop();
        var viewportBottom = viewportTop + $(window).height();
        return elementBottom > viewportTop && elementTop < viewportBottom;
    }

    // Listen for scroll events to trigger animations when elements come into view
    $(window).on('scroll', function() {
        if (isElementInView($('#carouselExample'))) {
            $('#carouselExample').addClass('fade-in');
        }
        $('.invisible-section').each(function() {
            if (isElementInView($(this))) {
                $(this).addClass('fade-in');
            }
        });
    });

    // Trigger the scroll event on page load
    $(window).scroll();

    // Hover animations for text columns and cards
    $('.col.fs-4 p').hover(
        function() {
            $(this).addClass('box-color3 fs-3').removeClass('fs-4');
        }, 
        function() {
            $(this).removeClass('box-color3 fs-3').addClass('fs-4');
        }
    );

    $('.card').hover(
        function() {
            $(this).addClass('highlighted');
        },
        function() {
            $(this).removeClass('highlighted');
        }
    );

    $('.card.box-color3.rounded-5.border-dark').hover(
        function() {
            $(this).addClass('highlighted');
        },
        function() {
            $(this).removeClass('highlighted');
        }
    );

    // Dropdown item selection and download functionality
    $('.dropdown-item').click(function() {
        var filename = $(this).attr('data-filename');
        var downloadLink = $('#downloadLink');
        downloadLink.attr('href', `/download_plate/${filename}`);
        $('#dropdownMenuButton').text($(this).text());
    });
});