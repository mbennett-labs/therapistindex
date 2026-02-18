<?php
/**
 * TherapistIndex — GeoDirectory Custom Fields Setup
 *
 * Creates all 28 custom fields for the gd_place post type.
 * Field slugs match prepare_import.py GEODIR_COLUMN_MAP exactly.
 *
 * USAGE (pick one):
 *
 *   Option A — WP-CLI (recommended):
 *     wp eval-file custom_fields_setup.php
 *
 *   Option B — Must-Use Plugin (auto-runs once):
 *     1. Upload this file to wp-content/mu-plugins/custom_fields_setup.php
 *     2. Visit /wp-admin/ once (fields are created on admin_init)
 *     3. Delete the file from mu-plugins/ after it runs
 *
 *   Option C — Paste into functions.php temporarily:
 *     1. Add:  require_once __DIR__ . '/custom_fields_setup.php';
 *        to the bottom of wp-content/themes/astra/functions.php
 *     2. Visit /wp-admin/ once
 *     3. Remove the require_once line
 *
 * The script checks for existing fields and skips duplicates, so it is
 * safe to run multiple times.
 *
 * @package TherapistIndex
 */

// Safety: bail if GeoDirectory is not active.
if ( ! function_exists( 'geodir_custom_field_save' ) ) {
    if ( defined( 'WP_CLI' ) && WP_CLI ) {
        WP_CLI::error( 'GeoDirectory plugin is not active. Activate it first.' );
    }
    return;
}

/**
 * Run the field creation. Wrapped in a function so it can be called
 * from admin_init (mu-plugin) or directly (WP-CLI).
 */
function therapistindex_create_custom_fields() {

    // Prevent running more than once per request.
    static $has_run = false;
    if ( $has_run ) {
        return;
    }
    $has_run = true;

    // One-time flag — if fields were already created, skip.
    $flag = get_option( 'therapistindex_fields_created' );
    if ( $flag === 'yes' ) {
        therapistindex_log( 'Fields already created (option flag set). Skipping.' );
        return;
    }

    $post_type = 'gd_place';
    $created   = 0;
    $skipped   = 0;

    // ──────────────────────────────────────────────────────────────
    // Define all custom fields.
    // GeoDirectory prepends "geodir_" to htmlvar_name automatically,
    // so htmlvar_name "practice_name" becomes "geodir_practice_name"
    // in the DB and front-end CSS classes.
    // ──────────────────────────────────────────────────────────────

    $fields = array(

        // ── Contact / Identity ──────────────────────────────────
        array(
            'htmlvar_name'   => 'practice_name',
            'admin_title'    => 'Practice Name',
            'frontend_title' => 'Practice Name',
            'field_type'     => 'text',
            'data_type'      => 'VARCHAR',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing],[mapbubble]',
            'sort_order'     => 1,
        ),
        array(
            'htmlvar_name'   => 'contact_phone',
            'admin_title'    => 'Contact Phone',
            'frontend_title' => 'Phone',
            'field_type'     => 'phone',
            'data_type'      => 'VARCHAR',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing],[mapbubble]',
            'sort_order'     => 2,
        ),
        array(
            'htmlvar_name'   => 'email',
            'admin_title'    => 'Email Address',
            'frontend_title' => 'Email',
            'field_type'     => 'email',
            'data_type'      => 'VARCHAR',
            'is_required'    => 0,
            'show_in'        => '[detail]',
            'sort_order'     => 3,
        ),
        array(
            'htmlvar_name'   => 'website',
            'admin_title'    => 'Website',
            'frontend_title' => 'Website',
            'field_type'     => 'url',
            'data_type'      => 'VARCHAR',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 4,
        ),

        // ── Licensing ───────────────────────────────────────────
        array(
            'htmlvar_name'   => 'license_type',
            'admin_title'    => 'License Type',
            'frontend_title' => 'License Type',
            'field_type'     => 'select',
            'data_type'      => 'VARCHAR',
            'option_values'  => 'Select License Type/,LCSW,LCSW-C,LPC,LCPC,LMFT,LCMFT,PsyD,PhD,MD/Psychiatrist,LMSW,LGSW,LGPC',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 5,
        ),
        array(
            'htmlvar_name'   => 'license_number',
            'admin_title'    => 'License Number',
            'frontend_title' => 'License #',
            'field_type'     => 'text',
            'data_type'      => 'VARCHAR',
            'is_required'    => 0,
            'show_in'        => '[detail]',
            'sort_order'     => 6,
        ),
        array(
            'htmlvar_name'   => 'license_state',
            'admin_title'    => 'License State',
            'frontend_title' => 'Licensed In',
            'field_type'     => 'select',
            'data_type'      => 'VARCHAR',
            'option_values'  => 'Select State/,DC,MD,VA,PA,DE,WV,AL,AK,AZ,AR,CA,CO,CT,FL,GA,HI,ID,IL,IN,IA,KS,KY,LA,ME,MA,MI,MN,MS,MO,MT,NE,NV,NH,NJ,NM,NY,NC,ND,OH,OK,OR,RI,SC,SD,TN,TX,UT,VT,WA,WI,WY',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 7,
        ),
        array(
            'htmlvar_name'   => 'license_verified',
            'admin_title'    => 'License Verified',
            'frontend_title' => 'License Verified',
            'field_type'     => 'checkbox',
            'data_type'      => 'TINYINT',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 8,
        ),

        // ── Clinical Info ───────────────────────────────────────
        array(
            'htmlvar_name'   => 'specializations',
            'admin_title'    => 'Specializations',
            'frontend_title' => 'Specializations',
            'field_type'     => 'multiselect',
            'data_type'      => 'VARCHAR',
            'extra_fields'   => array( 'data_type' => 'TEXT' ),
            'option_values'  => 'Anxiety,Depression,PTSD/Trauma,Couples/Marriage,LGBTQ+,Grief,Addiction,ADHD,OCD,Eating Disorders,Child/Adolescent,Family,Anger Management,Life Transitions,Chronic Illness,Perinatal/Postpartum,Bipolar Disorder,Personality Disorders,Self-Harm,Stress Management,Sleep Issues,Autism Spectrum',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 9,
        ),
        array(
            'htmlvar_name'   => 'therapy_approaches',
            'admin_title'    => 'Therapy Approaches',
            'frontend_title' => 'Therapy Approaches',
            'field_type'     => 'multiselect',
            'data_type'      => 'VARCHAR',
            'extra_fields'   => array( 'data_type' => 'TEXT' ),
            'option_values'  => 'CBT,DBT,EMDR,Psychodynamic,Humanistic,Solution-Focused,ACT,Mindfulness-Based,Play Therapy,Art Therapy,Somatic,Gottman Method,IFS,EFT,Motivational Interviewing,Narrative Therapy',
            'is_required'    => 0,
            'show_in'        => '[detail]',
            'sort_order'     => 10,
        ),
        array(
            'htmlvar_name'   => 'age_groups_served',
            'admin_title'    => 'Age Groups Served',
            'frontend_title' => 'Ages Served',
            'field_type'     => 'multiselect',
            'data_type'      => 'VARCHAR',
            'extra_fields'   => array( 'data_type' => 'TEXT' ),
            'option_values'  => 'Children 0-12,Adolescents 13-17,Adults 18-64,Seniors 65+,Couples,Families,Groups',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 11,
        ),

        // ── Insurance & Pricing ─────────────────────────────────
        array(
            'htmlvar_name'   => 'insurance_accepted',
            'admin_title'    => 'Insurance Accepted',
            'frontend_title' => 'Insurance Accepted',
            'field_type'     => 'multiselect',
            'data_type'      => 'VARCHAR',
            'extra_fields'   => array( 'data_type' => 'TEXT' ),
            'option_values'  => 'Aetna,Anthem,BlueCross BlueShield,CareFirst,Cigna,Humana,Kaiser Permanente,Magellan,Medicaid,Medicare,Tricare,UnitedHealthcare,Amerigroup,Beacon Health,Compsych,Highmark,Johns Hopkins EHP,Lyra Health,MedStar Family Choice,Molina Healthcare,Sentara Health Plans,Virginia Premier,Out-of-Network,Self-Pay Only',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 12,
        ),
        array(
            'htmlvar_name'   => 'sliding_scale',
            'admin_title'    => 'Sliding Scale',
            'frontend_title' => 'Sliding Scale',
            'field_type'     => 'select',
            'data_type'      => 'VARCHAR',
            'option_values'  => 'Unknown/,Yes,No,Unknown',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 13,
        ),
        array(
            'htmlvar_name'   => 'price_range_min',
            'admin_title'    => 'Price Range Min ($)',
            'frontend_title' => 'Starting At',
            'field_type'     => 'text',
            'data_type'      => 'INT',
            'is_required'    => 0,
            'show_in'        => '[detail]',
            'sort_order'     => 14,
        ),
        array(
            'htmlvar_name'   => 'price_range_max',
            'admin_title'    => 'Price Range Max ($)',
            'frontend_title' => 'Up To',
            'field_type'     => 'text',
            'data_type'      => 'INT',
            'is_required'    => 0,
            'show_in'        => '[detail]',
            'sort_order'     => 15,
        ),
        array(
            'htmlvar_name'   => 'session_length',
            'admin_title'    => 'Session Length',
            'frontend_title' => 'Session Length',
            'field_type'     => 'select',
            'data_type'      => 'VARCHAR',
            'option_values'  => 'Select/,30min,45min,50min,60min,90min',
            'is_required'    => 0,
            'show_in'        => '[detail]',
            'sort_order'     => 16,
        ),

        // ── Availability ────────────────────────────────────────
        array(
            'htmlvar_name'   => 'telehealth',
            'admin_title'    => 'Telehealth Available',
            'frontend_title' => 'Telehealth',
            'field_type'     => 'select',
            'data_type'      => 'VARCHAR',
            'option_values'  => 'Unknown/,Yes - Video,Yes - Phone,Yes - Both,No,Unknown',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing],[mapbubble]',
            'sort_order'     => 17,
        ),
        array(
            'htmlvar_name'   => 'telehealth_platform',
            'admin_title'    => 'Telehealth Platform',
            'frontend_title' => 'Telehealth Platform',
            'field_type'     => 'text',
            'data_type'      => 'VARCHAR',
            'is_required'    => 0,
            'show_in'        => '[detail]',
            'sort_order'     => 18,
        ),
        array(
            'htmlvar_name'   => 'accepting_new_patients',
            'admin_title'    => 'Accepting New Patients',
            'frontend_title' => 'Accepting New Patients',
            'field_type'     => 'select',
            'data_type'      => 'VARCHAR',
            'option_values'  => 'Unknown/,Yes,No,Waitlist,Unknown',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing],[mapbubble]',
            'sort_order'     => 19,
        ),
        array(
            'htmlvar_name'   => 'wait_time',
            'admin_title'    => 'Wait Time',
            'frontend_title' => 'Estimated Wait',
            'field_type'     => 'select',
            'data_type'      => 'VARCHAR',
            'option_values'  => 'Unknown/,Immediate,1-2 weeks,2-4 weeks,1+ month,Unknown',
            'is_required'    => 0,
            'show_in'        => '[detail]',
            'sort_order'     => 20,
        ),

        // ── Demographics / About ────────────────────────────────
        array(
            'htmlvar_name'   => 'languages',
            'admin_title'    => 'Languages Spoken',
            'frontend_title' => 'Languages',
            'field_type'     => 'multiselect',
            'data_type'      => 'VARCHAR',
            'extra_fields'   => array( 'data_type' => 'TEXT' ),
            'option_values'  => 'English,Spanish,Mandarin,Korean,Vietnamese,ASL,French,Arabic,Amharic,Portuguese,Hindi,Urdu,Tagalog,Farsi,Russian,Japanese,German,Italian,Haitian Creole,Other',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 21,
        ),
        array(
            'htmlvar_name'   => 'gender',
            'admin_title'    => 'Gender',
            'frontend_title' => 'Gender',
            'field_type'     => 'select',
            'data_type'      => 'VARCHAR',
            'option_values'  => 'Select/,Male,Female,Non-Binary,Prefer not to say',
            'is_required'    => 0,
            'show_in'        => '[detail]',
            'sort_order'     => 22,
        ),
        array(
            'htmlvar_name'   => 'years_experience',
            'admin_title'    => 'Years of Experience',
            'frontend_title' => 'Years Experience',
            'field_type'     => 'text',
            'data_type'      => 'INT',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 23,
        ),
        array(
            'htmlvar_name'   => 'education',
            'admin_title'    => 'Education / Credentials',
            'frontend_title' => 'Education',
            'field_type'     => 'textarea',
            'data_type'      => 'TEXT',
            'is_required'    => 0,
            'show_in'        => '[detail]',
            'sort_order'     => 24,
        ),
        array(
            'htmlvar_name'   => 'profile_image_url',
            'admin_title'    => 'Profile Image URL',
            'frontend_title' => 'Profile Photo',
            'field_type'     => 'url',
            'data_type'      => 'VARCHAR',
            'is_required'    => 0,
            'show_in'        => '',
            'sort_order'     => 25,
        ),

        // ── Data Quality / Internal ─────────────────────────────
        array(
            'htmlvar_name'   => 'google_rating',
            'admin_title'    => 'Google Rating',
            'frontend_title' => 'Google Rating',
            'field_type'     => 'text',
            'data_type'      => 'FLOAT',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 26,
        ),
        array(
            'htmlvar_name'   => 'google_review_count',
            'admin_title'    => 'Google Review Count',
            'frontend_title' => 'Reviews',
            'field_type'     => 'text',
            'data_type'      => 'INT',
            'is_required'    => 0,
            'show_in'        => '[detail],[listing]',
            'sort_order'     => 27,
        ),
        array(
            'htmlvar_name'   => 'last_verified_date',
            'admin_title'    => 'Last Verified Date',
            'frontend_title' => 'Last Verified',
            'field_type'     => 'datepicker',
            'data_type'      => 'DATE',
            'extra_fields'   => array( 'date_format' => 'Y-m-d' ),
            'is_required'    => 0,
            'show_in'        => '[detail]',
            'sort_order'     => 28,
        ),
        array(
            'htmlvar_name'   => 'data_source',
            'admin_title'    => 'Data Source',
            'frontend_title' => 'Source',
            'field_type'     => 'text',
            'data_type'      => 'VARCHAR',
            'is_required'    => 0,
            'show_in'        => '',
            'sort_order'     => 29,
        ),
        array(
            'htmlvar_name'   => 'enrichment_status',
            'admin_title'    => 'Enrichment Status',
            'frontend_title' => 'Data Quality',
            'field_type'     => 'select',
            'data_type'      => 'VARCHAR',
            'option_values'  => 'raw/,raw,cleaned,enriched_basic,enriched_full,verified',
            'is_required'    => 0,
            'show_in'        => '',
            'sort_order'     => 30,
        ),
    );

    therapistindex_log( '========================================' );
    therapistindex_log( 'TherapistIndex: Creating GeoDirectory custom fields' );
    therapistindex_log( sprintf( 'Fields to process: %d', count( $fields ) ) );
    therapistindex_log( '========================================' );

    foreach ( $fields as $field_def ) {
        $slug = $field_def['htmlvar_name'];

        // Check if field already exists.
        if ( therapistindex_field_exists( $slug, $post_type ) ) {
            therapistindex_log( sprintf( '  SKIP: geodir_%s (already exists)', $slug ) );
            $skipped++;
            continue;
        }

        // Build the full field array for geodir_custom_field_save().
        $field = array(
            'post_type'      => $post_type,
            'field_type'     => $field_def['field_type'],
            'field_type_key' => $field_def['field_type'],
            'data_type'      => $field_def['data_type'],
            'admin_title'    => $field_def['admin_title'],
            'frontend_title' => $field_def['frontend_title'],
            'htmlvar_name'   => $slug,
            'default_value'  => isset( $field_def['default_value'] ) ? $field_def['default_value'] : '',
            'option_values'  => isset( $field_def['option_values'] ) ? $field_def['option_values'] : '',
            'is_active'      => 1,
            'is_default'     => 0,
            'is_required'    => isset( $field_def['is_required'] ) ? $field_def['is_required'] : 0,
            'show_in'        => isset( $field_def['show_in'] ) ? $field_def['show_in'] : '[detail]',
            'sort_order'     => isset( $field_def['sort_order'] ) ? $field_def['sort_order'] : 99,
            'for_admin_use'  => false,
        );

        // Extra fields (date format, data type override for multiselect, etc.)
        if ( isset( $field_def['extra_fields'] ) ) {
            $field['extra'] = $field_def['extra_fields'];
            // For multiselect, GD needs TEXT data type to store comma-separated values.
            if ( isset( $field_def['extra_fields']['data_type'] ) ) {
                $field['data_type'] = $field_def['extra_fields']['data_type'];
            }
        }

        // Save the field.
        $result = geodir_custom_field_save( $field );

        if ( is_wp_error( $result ) ) {
            therapistindex_log( sprintf(
                '  ERROR: geodir_%s — %s',
                $slug,
                $result->get_error_message()
            ) );
        } elseif ( $result ) {
            therapistindex_log( sprintf(
                '  OK: geodir_%s (%s, %s)',
                $slug,
                $field_def['field_type'],
                $field_def['data_type']
            ) );
            $created++;
        } else {
            therapistindex_log( sprintf( '  WARN: geodir_%s — returned false/empty', $slug ) );
        }
    }

    // Set flag so we don't run again.
    update_option( 'therapistindex_fields_created', 'yes' );

    therapistindex_log( '========================================' );
    therapistindex_log( sprintf( 'Done. Created: %d  |  Skipped: %d  |  Total: %d', $created, $skipped, count( $fields ) ) );
    therapistindex_log( '========================================' );
    therapistindex_log( '' );
    therapistindex_log( 'NEXT STEPS:' );
    therapistindex_log( '  1. Go to WP Admin > GeoDirectory > Custom Fields to verify' );
    therapistindex_log( '  2. Adjust field order / visibility as needed' );
    therapistindex_log( '  3. Import data via GeoDirectory > Import/Export' );
    therapistindex_log( '  4. Remove this script from mu-plugins (if applicable)' );
}


/**
 * Check if a GeoDirectory custom field already exists for a post type.
 *
 * @param string $htmlvar_name Field slug (without geodir_ prefix).
 * @param string $post_type    GD post type.
 * @return bool
 */
function therapistindex_field_exists( $htmlvar_name, $post_type ) {
    global $wpdb;

    $table = $wpdb->prefix . 'geodir_custom_fields';

    // Verify the table exists (safety check).
    if ( $wpdb->get_var( $wpdb->prepare( 'SHOW TABLES LIKE %s', $table ) ) !== $table ) {
        return false;
    }

    $exists = $wpdb->get_var( $wpdb->prepare(
        "SELECT id FROM {$table} WHERE htmlvar_name = %s AND post_type = %s LIMIT 1",
        $htmlvar_name,
        $post_type
    ) );

    return ! empty( $exists );
}


/**
 * Log a message to WP-CLI or error_log.
 *
 * @param string $message
 */
function therapistindex_log( $message ) {
    if ( defined( 'WP_CLI' ) && WP_CLI ) {
        WP_CLI::log( $message );
    } else {
        error_log( '[TherapistIndex] ' . $message );
    }
}


// ──────────────────────────────────────────────────────────────────
// EXECUTION: Decide how to run based on context.
// ──────────────────────────────────────────────────────────────────

if ( defined( 'WP_CLI' ) && WP_CLI ) {
    // WP-CLI: run immediately.
    therapistindex_create_custom_fields();
} else {
    // mu-plugin or functions.php: run on admin_init (needs admin context).
    add_action( 'admin_init', 'therapistindex_create_custom_fields' );
}
