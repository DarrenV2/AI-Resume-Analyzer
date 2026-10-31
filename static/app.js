// ===== Settings =====

// Display text for the values the API sends (the values match schemas.py)
const STATUS_LABELS = {
    strong_evidence: "Strong evidence",
    partial_evidence: "Partial evidence",
    not_identified: "Not identified",
    needs_review: "Needs review",
};

const PRIORITY_LABELS = {
    required: "Required",
    preferred: "Preferred",
    unspecified: "Priority unspecified",
};


// ===== Page elements (ids from index.html) =====

const form = document.getElementById("analyze-form");
const submitButton = document.getElementById("analyze-button");
const statusBox = document.getElementById("status");
const resultsSection = document.getElementById("results");
const jobTitleHeading = document.getElementById("job-title");
const summaryText = document.getElementById("summary");
const countsList = document.getElementById("counts");
const requirementsList = document.getElementById("requirements");
const strengthsList = document.getElementById("strengths");
const prioritiesList = document.getElementById("improvement-priorities");

form.addEventListener("submit", handleSubmit);


// ===== Sending the form =====

async function handleSubmit(event) {
    // Stop the browser's default submit, which would reload the page
    event.preventDefault();

    // Disabled while waiting, so the same resume can't be sent twice
    submitButton.disabled = true;
    resultsSection.hidden = true;
    showStatus("Analyzing your resume. This can take up to a minute...", false);

    try {
        // No Content-Type header: the browser sets the multipart format for FormData itself
        const response = await fetch("/analyze", {
            method: "POST",
            body: new FormData(form),
        });
        const data = await response.json();

        if (response.ok) {
            hideStatus();
            showResults(data);
        } else {
            showStatus(errorMessage(data), true);
        }
    } catch (error) {
        // fetch fails if the server can't be reached; json() fails if the reply isn't JSON
        console.error(error);
        showStatus("Could not get a response from the server. Check that it's running and try again.", true);
    } finally {
        submitButton.disabled = false;
    }
}


// detail is the route's friendly message, except for 422 errors, where FastAPI sends a list
function errorMessage(data) {
    if (typeof data.detail === "string") {
        return data.detail;
    }
    return "Please check the form and try again.";
}


// ===== Showing the results =====
// All text goes in through makeElement or textContent, never innerHTML: resume quotes are
// copied from an untrusted upload, and innerHTML would run any HTML hidden in them (XSS)

function showResults(data) {
    resultsSection.hidden = false;
    jobTitleHeading.textContent = data.job_title || "Resume analysis";
    summaryText.textContent = data.summary;

    showCounts(data.requirements);

    requirementsList.replaceChildren();
    for (const match of data.requirements) {
        requirementsList.append(makeRequirementCard(match));
    }

    fillList(strengthsList, data.strengths);
    fillList(prioritiesList, data.improvement_priorities);
}


// The counts are calculated here, not asked from the AI, so they always match the cards
function showCounts(requirements) {
    const counts = {strong_evidence: 0, partial_evidence: 0, not_identified: 0, needs_review: 0};
    for (const match of requirements) {
        counts[match.status] += 1;
    }

    countsList.replaceChildren();
    for (const status of Object.keys(counts)) {
        const item = makeElement("li", "status-" + status);
        item.append(makeElement("span", "count", counts[status]), " " + STATUS_LABELS[status]);
        countsList.append(item);
    }
}


// Builds one card in the structure described in index.html above <div id="requirements">
function makeRequirementCard(match) {
    const card = makeElement("article", "requirement");

    const header = makeElement("div", "requirement-header");
    header.append(
        makeElement("h4", "", match.requirement),
        makeElement("span", "badge priority", PRIORITY_LABELS[match.priority]),
        makeElement("span", "badge status-" + match.status, STATUS_LABELS[match.status])
    );
    card.append(header);

    // Skipped when no evidence was identified (an empty list)
    if (match.resume_evidence.length > 0) {
        card.append(makeElement("p", "label", "Evidence from your resume"));
        for (const quote of match.resume_evidence) {
            card.append(makeElement("blockquote", "", quote));
        }
    }

    card.append(makeElement("p", "label", "Reasoning"));
    card.append(makeElement("p", "", match.reasoning));

    // Skipped when the AI gave no suggestion (null)
    if (match.suggestion) {
        card.append(makeElement("p", "label", "Suggestion"));
        card.append(makeElement("p", "suggestion", match.suggestion));
    }

    return card;
}


function fillList(listElement, items) {
    // Clears the previous analysis's items, so a second analysis doesn't add to the first
    listElement.replaceChildren();
    for (const text of items) {
        listElement.append(makeElement("li", "", text));
    }
}


// ===== Helpers =====

function showStatus(message, isError) {
    statusBox.textContent = message;
    statusBox.className = isError ? "error" : "";
    statusBox.hidden = false;
}


function hideStatus() {
    statusBox.hidden = true;
}


function makeElement(tag, className, text = "") {
    const element = document.createElement(tag);
    if (className) {
        element.className = className;
    }
    element.textContent = text;
    return element;
}
