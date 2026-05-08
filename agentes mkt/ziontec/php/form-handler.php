<?php
// ============================================
// ZIONTEC — Form Handler
// Update $to_email with your real email address
// ============================================

header('Content-Type: application/json');

// ─── CONFIG ──────────────────────────────────────────────────────────────────
$to_email   = 'contact@ziontecpower.com'; // <-- UPDATE THIS
$from_email = 'noreply@ziontecpower.com';
$site_name  = 'Ziontec';

// ─── VALIDATION ──────────────────────────────────────────────────────────────
function sanitize($value) {
    return htmlspecialchars(strip_tags(trim($value)));
}

$required = ['firstName', 'lastName', 'email', 'phone', 'address', 'state', 'propertyType', 'services'];

foreach ($required as $field) {
    if (empty($_POST[$field])) {
        echo json_encode(['success' => false, 'message' => 'Missing required field: ' . $field]);
        exit;
    }
}

$email = filter_var($_POST['email'], FILTER_VALIDATE_EMAIL);
if (!$email) {
    echo json_encode(['success' => false, 'message' => 'Invalid email address.']);
    exit;
}

// ─── COLLECT DATA ────────────────────────────────────────────────────────────
$firstName     = sanitize($_POST['firstName']);
$lastName      = sanitize($_POST['lastName']);
$phone         = sanitize($_POST['phone']);
$address       = sanitize($_POST['address']);
$state         = sanitize($_POST['state']);
$propertyType  = sanitize($_POST['propertyType']);
$services      = sanitize($_POST['services']);
$evBrand       = sanitize($_POST['evBrand'] ?? '');
$preferredDate = sanitize($_POST['preferredDate'] ?? '');
$message       = sanitize($_POST['message'] ?? '');

// ─── SERVICE LABELS ──────────────────────────────────────────────────────────
$serviceLabels = [
    'ev_l2_residential'   => 'EV Charging — Level 2 (Residential)',
    'ev_commercial'       => 'EV Charging — Commercial (Level 2 + DC Fast)',
    'solar_residential'   => 'Solar Panels — Residential',
    'solar_commercial'    => 'Solar Panels — Commercial',
    'ev_solar_residential'=> 'EV Charging + Solar — Residential',
    'ev_solar_commercial' => 'EV Charging + Solar — Commercial',
];

$propertyLabels = [
    'residential_home'   => 'Residential — Single Family Home',
    'residential_condo'  => 'Residential — Condo/Townhouse',
    'commercial_small'   => 'Commercial — Small Business',
    'commercial_large'   => 'Commercial — Large/Multi-unit',
];

$serviceLabel  = $serviceLabels[$services]  ?? $services;
$propertyLabel = $propertyLabels[$propertyType] ?? $propertyType;

// ─── EMAIL BODY ──────────────────────────────────────────────────────────────
$subject = "New Assessment Request — {$firstName} {$lastName} ({$state})";

$body = "
==============================================
NEW FREE ASSESSMENT REQUEST — {$site_name}
==============================================

CONTACT INFORMATION
-------------------
Name:    {$firstName} {$lastName}
Email:   {$email}
Phone:   {$phone}
Address: {$address}
State:   {$state}

PROPERTY & SERVICE
------------------
Property Type: {$propertyLabel}
Service:       {$serviceLabel}
EV Brand:      " . ($evBrand ?: 'Not specified') . "
Preferred Date: " . ($preferredDate ?: 'Flexible') . "

ADDITIONAL NOTES
----------------
{$message}

==============================================
Submitted: " . date('Y-m-d H:i:s') . "
IP: " . $_SERVER['REMOTE_ADDR'] . "
==============================================
";

// ─── SEND EMAIL ──────────────────────────────────────────────────────────────
$headers  = "From: {$site_name} <{$from_email}>\r\n";
$headers .= "Reply-To: {$email}\r\n";
$headers .= "X-Mailer: PHP/" . phpversion() . "\r\n";

$sent = mail($to_email, $subject, $body, $headers);

// ─── AUTO-REPLY TO CUSTOMER ──────────────────────────────────────────────────
if ($sent) {
    $autoSubject = "We received your request, {$firstName}! — {$site_name}";
    $autoBody = "Hi {$firstName},

Thank you for requesting a free site assessment with Ziontec!

We received your request and our team will contact you within 1 business day to confirm your on-site visit.

YOUR REQUEST SUMMARY
--------------------
Service: {$serviceLabel}
Address: {$address}, {$state}
Preferred Date: " . ($preferredDate ?: 'Flexible') . "

WHAT HAPPENS NEXT
-----------------
1. We'll call or email you within 1 business day
2. We'll schedule your on-site visit at your convenience
3. Assessment takes 45-60 minutes — you'll get a quote the same day
4. No pressure, no obligation

If you have any urgent questions, call or text us at (781) 866-7085.

Charge Everything. Depend on Nothing.

— The Ziontec Team
contact@ziontecpower.com
(781) 866-7085
www.ziontec.com

Serving Massachusetts · Connecticut · Rhode Island · New Hampshire · Vermont · Maine
";

    $autoHeaders  = "From: {$site_name} <{$from_email}>\r\n";
    $autoHeaders .= "Reply-To: {$to_email}\r\n";
    mail($email, $autoSubject, $autoBody, $autoHeaders);

    echo json_encode(['success' => true]);
} else {
    echo json_encode(['success' => false, 'message' => 'Mail server error. Please call us directly.']);
}
?>
