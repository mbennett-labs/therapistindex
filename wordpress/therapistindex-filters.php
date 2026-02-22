<?php
/**
 * Plugin Name: TherapistIndex Filters
 * Description: Custom filter bar for /places/ archive, GeoDirectory query hooks, and logo for TherapistIndex.com
 * Version: 1.0
 * Author: Mike Bennett
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * ========================================================================
 * 1. FILTER CONFIGURATION
 * ========================================================================
 */

function ti_get_filter_config() {
    return array(
        'ti_insurance' => array(
            'column'  => 'insurance_accepted',
            'label'   => 'Insurance',
            'type'    => 'select',
            'match'   => 'like',
            'options' => array(
                'Aetna', 'Anthem', 'BlueCross BlueShield', 'CareFirst', 'Cigna',
                'Humana', 'Kaiser Permanente', 'Medicaid', 'Medicare', 'Tricare',
                'UnitedHealthcare', 'Self-Pay Only',
            ),
        ),
        'ti_telehealth' => array(
            'column'  => 'telehealth',
            'label'   => 'Telehealth',
            'type'    => 'toggle',
            'match'   => 'like',
            'search'  => 'Yes',
        ),
        'ti_specialty' => array(
            'column'  => 'specializations',
            'label'   => 'Specialty',
            'type'    => 'select',
            'match'   => 'like',
            'options' => array(
                'Anxiety', 'Depression', 'PTSD/Trauma', 'Couples/Marriage', 'LGBTQ+',
                'Grief', 'Addiction', 'ADHD', 'OCD', 'Eating Disorders',
                'Child/Adolescent', 'Family', 'Anger Management', 'Life Transitions',
                'Chronic Illness', 'Perinatal/Postpartum', 'Bipolar Disorder',
                'Personality Disorders', 'Stress Management', 'Sleep Issues', 'Autism Spectrum',
            ),
        ),
        'ti_accepting' => array(
            'column'  => 'accepting_new_patients',
            'label'   => 'Accepting New Patients',
            'type'    => 'toggle',
            'match'   => 'equals',
            'search'  => 'Yes',
        ),
    );
}


/**
 * ========================================================================
 * 2. RENDER FILTER FORM (above listing grid on GD archive pages)
 * ========================================================================
 */

add_action( 'geodir_before_listing_listview', 'ti_render_filter_form' );

function ti_render_filter_form() {
    $filters = ti_get_filter_config();

    // Build current URL base (archive page without our filter params)
    $base_url = strtok( $_SERVER['REQUEST_URI'], '?' );

    // Check if any filters are active
    $has_active = false;
    foreach ( $filters as $param => $cfg ) {
        if ( ! empty( $_GET[ $param ] ) ) {
            $has_active = true;
            break;
        }
    }

    ?>
    <div class="ti-filter-bar" id="ti-filters">
        <form method="get" action="<?php echo esc_url( $base_url ); ?>" class="ti-filter-form">
            <?php
            // Preserve any existing GD search params (s, snear, etc.)
            foreach ( $_GET as $key => $val ) {
                if ( strpos( $key, 'ti_' ) === 0 ) continue;
                if ( is_string( $val ) ) {
                    printf(
                        '<input type="hidden" name="%s" value="%s">',
                        esc_attr( $key ),
                        esc_attr( $val )
                    );
                }
            }
            ?>

            <div class="ti-filter-fields">
                <?php foreach ( $filters as $param => $cfg ) : ?>
                    <?php if ( $cfg['type'] === 'select' ) : ?>
                        <div class="ti-filter-field ti-filter-select">
                            <label for="<?php echo esc_attr( $param ); ?>"><?php echo esc_html( $cfg['label'] ); ?></label>
                            <select name="<?php echo esc_attr( $param ); ?>" id="<?php echo esc_attr( $param ); ?>">
                                <option value="">All <?php echo esc_html( $cfg['label'] ); ?></option>
                                <?php foreach ( $cfg['options'] as $opt ) : ?>
                                    <option value="<?php echo esc_attr( $opt ); ?>"
                                        <?php selected( isset( $_GET[ $param ] ) ? $_GET[ $param ] : '', $opt ); ?>>
                                        <?php echo esc_html( $opt ); ?>
                                    </option>
                                <?php endforeach; ?>
                            </select>
                        </div>
                    <?php elseif ( $cfg['type'] === 'toggle' ) : ?>
                        <div class="ti-filter-field ti-filter-toggle">
                            <label class="ti-toggle-label">
                                <input type="checkbox"
                                       name="<?php echo esc_attr( $param ); ?>"
                                       value="1"
                                       <?php checked( ! empty( $_GET[ $param ] ) ); ?>>
                                <span class="ti-toggle-switch"></span>
                                <span class="ti-toggle-text"><?php echo esc_html( $cfg['label'] ); ?></span>
                            </label>
                        </div>
                    <?php endif; ?>
                <?php endforeach; ?>

                <div class="ti-filter-actions">
                    <button type="submit" class="ti-filter-btn">Filter</button>
                    <?php if ( $has_active ) : ?>
                        <a href="<?php echo esc_url( $base_url ); ?>" class="ti-filter-clear">Clear</a>
                    <?php endif; ?>
                </div>
            </div>
        </form>
    </div>
    <?php
}


/**
 * ========================================================================
 * 3. FILTER THE GEODIRECTORY QUERY (SQL WHERE clauses)
 * ========================================================================
 */

add_filter( 'geodir_main_query_posts_where', 'ti_filter_listings_where', 10, 3 );

function ti_filter_listings_where( $where, $query, $post_type ) {
    if ( is_admin() ) {
        return $where;
    }

    global $wpdb;

    $table   = geodir_db_cpt_table( $post_type );
    $filters = ti_get_filter_config();

    $added = '';
    foreach ( $filters as $param => $cfg ) {
        $value = isset( $_GET[ $param ] ) ? sanitize_text_field( wp_unslash( $_GET[ $param ] ) ) : '';

        if ( $value === '' || $value === '0' ) {
            continue;
        }

        $column = $cfg['column'];

        if ( $cfg['match'] === 'like' ) {
            // For toggle filters, use the predefined search value
            $search = ( $cfg['type'] === 'toggle' && isset( $cfg['search'] ) ) ? $cfg['search'] : $value;
            $clause = $wpdb->prepare(
                " AND `{$table}`.`{$column}` LIKE %s",
                '%' . $wpdb->esc_like( $search ) . '%'
            );
            $where .= $clause;
            $added .= $clause;
        } elseif ( $cfg['match'] === 'equals' ) {
            $search = isset( $cfg['search'] ) ? $cfg['search'] : $value;
            $clause = $wpdb->prepare(
                " AND `{$table}`.`{$column}` = %s",
                $search
            );
            $where .= $clause;
            $added .= $clause;
        }
    }

    return $where;
}


/**
 * ========================================================================
 * 4. PRESERVE FILTER PARAMS IN GEODIRECTORY PAGINATION
 * ========================================================================
 */

add_filter( 'geodir_pagination_params', 'ti_preserve_pagination_params' );

function ti_preserve_pagination_params( $params ) {
    $filters = ti_get_filter_config();
    foreach ( $filters as $param => $cfg ) {
        if ( ! empty( $_GET[ $param ] ) ) {
            $params[ $param ] = sanitize_text_field( wp_unslash( $_GET[ $param ] ) );
        }
    }
    return $params;
}

// Also hook into the pagination link directly
add_filter( 'paginate_links', 'ti_add_filter_params_to_pagination' );

function ti_add_filter_params_to_pagination( $link ) {
    if ( ! $link ) return $link;

    $filters = ti_get_filter_config();
    foreach ( $filters as $param => $cfg ) {
        if ( ! empty( $_GET[ $param ] ) ) {
            $link = add_query_arg( $param, rawurlencode( sanitize_text_field( wp_unslash( $_GET[ $param ] ) ) ), $link );
        }
    }
    return $link;
}


/**
 * ========================================================================
 * 5. CUSTOM LOGO (BlockStrap navbar-brand)
 *
 * BlockStrap uses <a class="navbar-brand"><img src="...Blockstrap-white.png">
 * We swap that image src with our logo via JS on DOMContentLoaded.
 * ========================================================================
 */

add_action( 'wp_body_open', 'ti_inject_logo' );

function ti_inject_logo() {
    $logo_url = content_url( '/uploads/TherapistIndexLogo.png' );
    ?>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        var brandImg = document.querySelector('.navbar-brand img');
        if (brandImg) {
            brandImg.src = '<?php echo esc_url( $logo_url ); ?>';
            brandImg.alt = '<?php echo esc_attr( get_bloginfo( 'name' ) ); ?>';
            brandImg.style.display = 'block';
            brandImg.style.maxHeight = '50px';
            brandImg.style.width = 'auto';
        }
    });
    </script>
    <?php
}


/**
 * ========================================================================
 * 6. OVERRIDE BADGE ATTRIBUTES ON ARCHIVE CARDS
 *
 * BlockStrap's gd-archive-item.html template part contains the
 * gd_simple_archive_item shortcode with default badge presets.
 * WP_Super_Duper uses its own wp_super_duper_widget_display_callback filter
 * (not WordPress shortcode_atts). We intercept there.
 * ========================================================================
 */

add_filter( 'wp_super_duper_widget_display_callback', 'ti_override_badge_atts', 10, 3 );

function ti_override_badge_atts( $args, $widget, $_instance ) {
    // Only target the gd_simple_archive_item widget
    if ( ! isset( $widget->base_id ) || $widget->base_id !== 'gd_simple_archive_item' ) {
        return $args;
    }

    // Top-left: Telehealth badge (blue)
    $args['top_left_badge_preset']    = 'custom';
    $args['top_left_badge_key']       = 'telehealth';
    $args['top_left_badge_condition'] = 'is_contains';
    $args['top_left_badge_search']    = 'Yes';
    $args['top_left_badge_icon_class'] = 'fas fa-video';
    $args['top_left_badge_badge']     = 'Telehealth';
    $args['top_left_badge_bg_color']  = '#2B6CB0';
    $args['top_left_badge_txt_color'] = '#ffffff';

    // Top-right: Accepting Patients badge (green)
    $args['top_right_badge_preset']    = 'custom';
    $args['top_right_badge_key']       = 'accepting_new_patients';
    $args['top_right_badge_condition'] = 'is_equal';
    $args['top_right_badge_search']    = 'Yes';
    $args['top_right_badge_icon_class'] = 'fas fa-user-plus';
    $args['top_right_badge_badge']     = 'Accepting Patients';
    $args['top_right_badge_bg_color']  = '#48BB78';
    $args['top_right_badge_txt_color'] = '#ffffff';

    // Bottom-left: Category (keep default)
    // Bottom-right: Favorite (keep default)

    return $args;
}


/**
 * ========================================================================
 * 7. FILTER BAR CSS
 * ========================================================================
 */

add_action( 'wp_head', 'ti_filter_bar_css' );

function ti_filter_bar_css() {
    ?>
    <style>
    /* ---- TherapistIndex Filter Bar ---- */
    .ti-filter-bar {
        max-width: 1200px;
        margin: 0 auto 1.5rem;
        padding: 1.25rem 1.5rem;
        background: var(--ti-white, #fff);
        border-radius: var(--ti-radius, 12px);
        box-shadow: var(--ti-shadow, 0 2px 8px rgba(0,0,0,0.06));
        border: 1px solid var(--ti-gray-200, #E2E8F0);
    }

    .ti-filter-form {
        margin: 0;
    }

    .ti-filter-fields {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        align-items: flex-end;
    }

    .ti-filter-field {
        flex: 1 1 200px;
        min-width: 0;
    }

    .ti-filter-field label:not(.ti-toggle-label) {
        display: block;
        font-size: 0.78rem;
        font-weight: 600;
        color: var(--ti-gray-500, #718096);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.35rem;
    }

    .ti-filter-field select {
        width: 100%;
        padding: 10px 14px;
        font-size: 0.92rem;
        font-family: var(--ti-font, 'Inter', sans-serif);
        border: 2px solid var(--ti-gray-200, #E2E8F0);
        border-radius: var(--ti-radius-sm, 8px);
        background: var(--ti-gray-50, #F7FAFC);
        color: var(--ti-gray-700, #2D3748);
        cursor: pointer;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
        appearance: none;
        -webkit-appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23718096' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 12px center;
        padding-right: 32px;
    }

    .ti-filter-field select:focus {
        border-color: var(--ti-blue, #2B6CB0);
        box-shadow: 0 0 0 3px rgba(43,108,176,0.12);
        outline: none;
        background-color: var(--ti-white, #fff);
    }

    /* Toggle switch */
    .ti-filter-toggle {
        flex: 0 0 auto;
        min-width: auto;
    }

    .ti-toggle-label {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        padding: 10px 0;
        font-size: 0.92rem;
        color: var(--ti-gray-700, #2D3748);
        user-select: none;
    }

    .ti-toggle-label input[type="checkbox"] {
        position: absolute;
        opacity: 0;
        width: 0;
        height: 0;
    }

    .ti-toggle-switch {
        position: relative;
        width: 42px;
        height: 24px;
        background: var(--ti-gray-300, #CBD5E0);
        border-radius: 12px;
        transition: background 0.2s ease;
        flex-shrink: 0;
    }

    .ti-toggle-switch::after {
        content: '';
        position: absolute;
        top: 2px;
        left: 2px;
        width: 20px;
        height: 20px;
        background: white;
        border-radius: 50%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        transition: transform 0.2s ease;
    }

    .ti-toggle-label input:checked + .ti-toggle-switch {
        background: var(--ti-blue, #2B6CB0);
    }

    .ti-toggle-label input:checked + .ti-toggle-switch::after {
        transform: translateX(18px);
    }

    .ti-toggle-text {
        font-weight: 500;
        white-space: nowrap;
    }

    /* Actions */
    .ti-filter-actions {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex: 0 0 auto;
        padding-top: 0;
    }

    .ti-filter-btn {
        padding: 10px 24px;
        font-size: 0.92rem;
        font-weight: 600;
        font-family: var(--ti-font, 'Inter', sans-serif);
        color: var(--ti-white, #fff);
        background: var(--ti-blue, #2B6CB0);
        border: none;
        border-radius: var(--ti-radius-sm, 8px);
        cursor: pointer;
        transition: background 0.2s ease, box-shadow 0.2s ease;
        white-space: nowrap;
    }

    .ti-filter-btn:hover {
        background: var(--ti-blue-dark, #1E4E8C);
        box-shadow: 0 4px 12px rgba(43,108,176,0.25);
    }

    .ti-filter-clear {
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--ti-gray-500, #718096);
        text-decoration: none;
        white-space: nowrap;
    }

    .ti-filter-clear:hover {
        color: var(--ti-blue, #2B6CB0);
        text-decoration: underline;
    }

    /* Responsive: tablet */
    @media (max-width: 991px) {
        .ti-filter-bar {
            margin: 0 1rem 1.5rem;
            padding: 1rem 1.25rem;
        }
        .ti-filter-field {
            flex: 1 1 180px;
        }
    }

    /* Responsive: mobile */
    @media (max-width: 575px) {
        .ti-filter-bar {
            margin: 0 0.5rem 1rem;
            padding: 1rem;
            border-radius: var(--ti-radius-sm, 8px);
        }
        .ti-filter-fields {
            flex-direction: column;
            gap: 0.75rem;
        }
        .ti-filter-field {
            flex: 1 1 100%;
        }
        .ti-filter-toggle {
            flex: 1 1 100%;
        }
        .ti-filter-actions {
            flex: 1 1 100%;
            justify-content: stretch;
        }
        .ti-filter-btn {
            flex: 1;
            width: 100%;
        }
    }
    /* ---- Logo: Override BlockStrap display:none on navbar-brand img ---- */
    .bsui .navbar-brand img {
        display: block !important;
        max-height: 50px !important;
        width: auto !important;
    }
    /* Hide the ::after text replacement when logo image is visible */
    .bsui .navbar-brand::after {
        display: none !important;
    }
    </style>
    <?php
}


/**
 * ========================================================================
 * 8. SEO TITLE TAG OVERRIDE FOR gd_place LISTINGS
 *
 * Replaces the default Yoast title "[Name] - therapistindex.com" with:
 * "[Name] — [Spec1] & [Spec2] Therapist in [City], [State] | Therapist Index"
 *
 * Fallbacks:
 *   - No specializations → "[Name] — Therapist in [City], [State] | Therapist Index"
 *   - No city            → "[Name] | Therapist Index"
 * ========================================================================
 */

add_filter( 'wpseo_title', 'ti_seo_title_gd_place', 20 );

function ti_seo_title_gd_place( $title ) {
    if ( ! is_singular( 'gd_place' ) ) {
        return $title;
    }

    $post_id = get_queried_object_id();
    if ( ! $post_id ) {
        return $title;
    }

    $name = get_the_title( $post_id );
    if ( ! $name ) {
        return $title;
    }

    $city   = geodir_get_post_meta( $post_id, 'city', true );
    $region = geodir_get_post_meta( $post_id, 'region', true );
    $specs  = geodir_get_post_meta( $post_id, 'specializations', true );

    // Build the specialization fragment (first 2 only)
    $spec_part = '';
    if ( ! empty( $specs ) ) {
        $spec_list = array_map( 'trim', explode( ',', $specs ) );
        $spec_list = array_filter( $spec_list );
        $spec_list = array_values( $spec_list );

        if ( count( $spec_list ) >= 2 ) {
            $spec_part = $spec_list[0] . ' & ' . $spec_list[1];
        } elseif ( count( $spec_list ) === 1 ) {
            $spec_part = $spec_list[0];
        }
    }

    // Build the location fragment
    $location_part = '';
    if ( ! empty( $city ) && ! empty( $region ) ) {
        $location_part = $city . ', ' . $region;
    } elseif ( ! empty( $city ) ) {
        $location_part = $city;
    } elseif ( ! empty( $region ) ) {
        $location_part = $region;
    }

    // No location data at all — simple fallback
    if ( empty( $location_part ) ) {
        return $name . ' | Therapist Index';
    }

    // Build the middle section
    if ( ! empty( $spec_part ) ) {
        $middle = $spec_part . ' Therapist in ' . $location_part;
    } else {
        $middle = 'Therapist in ' . $location_part;
    }

    return $name . ' — ' . $middle . ' | Therapist Index';
}


/**
 * ========================================================================
 * 9. SEO META DESCRIPTION OVERRIDE FOR gd_place LISTINGS
 *
 * Replaces the default Yoast meta description with:
 * "[Name] specializes in [Spec1], [Spec2] & [Spec3] therapy in [City], [State].
 *  View insurance, availability, contact info & more on Therapist Index."
 *
 * Fallbacks:
 *   - No specializations → "[Name] is a therapist in [City], [State]. ..."
 *   - No city            → "[Name] — View specialties, insurance, availability
 *                           & contact info on Therapist Index."
 * ========================================================================
 */

add_filter( 'wpseo_metadesc', 'ti_seo_metadesc_gd_place', 20 );

function ti_seo_metadesc_gd_place( $desc ) {
    if ( ! is_singular( 'gd_place' ) ) {
        return $desc;
    }

    $post_id = get_queried_object_id();
    if ( ! $post_id ) {
        return $desc;
    }

    $name = get_the_title( $post_id );
    if ( ! $name ) {
        return $desc;
    }

    $city   = geodir_get_post_meta( $post_id, 'city', true );
    $region = geodir_get_post_meta( $post_id, 'region', true );
    $specs  = geodir_get_post_meta( $post_id, 'specializations', true );

    // Build the specialization fragment (first 3 for descriptions — more room)
    $spec_part = '';
    if ( ! empty( $specs ) ) {
        $spec_list = array_map( 'trim', explode( ',', $specs ) );
        $spec_list = array_filter( $spec_list );
        $spec_list = array_values( $spec_list );

        if ( count( $spec_list ) >= 3 ) {
            $spec_part = $spec_list[0] . ', ' . $spec_list[1] . ' & ' . $spec_list[2];
        } elseif ( count( $spec_list ) === 2 ) {
            $spec_part = $spec_list[0] . ' & ' . $spec_list[1];
        } elseif ( count( $spec_list ) === 1 ) {
            $spec_part = $spec_list[0];
        }
    }

    // Build the location fragment
    $location_part = '';
    if ( ! empty( $city ) && ! empty( $region ) ) {
        $location_part = $city . ', ' . $region;
    } elseif ( ! empty( $city ) ) {
        $location_part = $city;
    } elseif ( ! empty( $region ) ) {
        $location_part = $region;
    }

    $cta = 'View insurance, availability, contact info & more on Therapist Index.';

    // No location — minimal fallback
    if ( empty( $location_part ) ) {
        return $name . ' — View specialties, insurance, availability & contact info on Therapist Index.';
    }

    // Build the opening sentence
    if ( ! empty( $spec_part ) ) {
        $opener = $name . ' specializes in ' . $spec_part . ' therapy in ' . $location_part . '.';
    } else {
        $opener = $name . ' is a therapist in ' . $location_part . '.';
    }

    return $opener . ' ' . $cta;
}

// Keep og:description in sync with the meta description
add_filter( 'wpseo_opengraph_desc', 'ti_seo_metadesc_gd_place', 20 );
