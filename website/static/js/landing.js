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
    const modalBody = document.getElementById('modalBody');
    const loadingSpinner = document.getElementById('loadingSpinner'); // Spinner element
    const responseContent = document.getElementById('responseContent'); // Response content element
    const submissionModal = new bootstrap.Modal(document.getElementById('submissionModal'));

    // Function to handle form submission and API request
    function submitForm(formData, apiUrl) {
        const payload = { prompt: formData.get('prompt') };

        // Show the modal, spinner, and clear previous content
        loadingSpinner.style.display = 'block';
        responseContent.textContent = ''; // Clear previous content
        submissionModal.show();

        fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            // Hide spinner once response is received
            loadingSpinner.style.display = 'none';
            if (data.error) {
                responseContent.textContent = JSON.stringify(data.error, null, 2);
            } else {
                responseContent.textContent = JSON.stringify(data.result, null, 2); // Show result
            }
        })
        .catch(error => {
            loadingSpinner.style.display = 'none';
            responseContent.textContent = 'An error occurred';
        });
    }

    // Event listener for thropicForm submit button
    submitBtn.addEventListener('click', function() {
        const formData = new FormData(thropicForm);
        submitForm(formData, '/rag-api');
    });

    // Event listener for sentimentForm submit button
    sentimentSubmitBtn.addEventListener('click', function() {
        const formData = new FormData(sentimentForm);
        submitForm(formData, '/sentiment-api');
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
