import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class FadeUpwardsCustomPageTransitionsBuilder extends PageTransitionsBuilder {
  const FadeUpwardsCustomPageTransitionsBuilder();

  @override
  Widget buildTransitions<T>(
    PageRoute<T> route,
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
    Widget child,
  ) {
    return FadeTransition(
      opacity: CurvedAnimation(
        parent: animation,
        curve: Curves.easeOut,
      ),
      child: SlideTransition(
        position: Tween<Offset>(
          begin: const Offset(0, 0.05), // A small fraction representing ~10px upward
          end: Offset.zero,
        ).animate(CurvedAnimation(
          parent: animation,
          curve: Curves.easeOut,
        )),
        child: child,
      ),
    );
  }
}

class AppTheme {
  // Colors - Deep forest green & fresh leaf
  static const Color primaryGreen = Color(0xFF1A4731);
  static const Color secondaryGreen = Color(0xFF2D6A4F);
  static const Color lightGreen = Color(0xFF40916C);
  
  static const Color background = Color(0xFFFAF8F2); // Off-white parchment
  static const Color surface = Color(0xFFFAF8F2); // Off-white parchment

  // Accent Colors
  static const Color accentGold = Color(0xFFE9C46A); // Warm gold/wheat
  static const Color accentOrange = Color(0xFFF4A261); // Sunset orange

  // Status Colors
  static const Color error = Color(0xFFE76F51); // Danger/down
  static const Color success = Color(0xFF52B788); // Success/up

  // Extended palette (used by screens)
  static const Color accentBlue = Color(0xFF3D8EBF); // info/forecast
  static const Color accentPurple = Color(0xFF7B61A0); // mandi/comparison

  static const Color textDark = Color(0xFF1A2E1A); // Dark text
  static const Color textMuted = Color(0xFF7A9A7A); // Muted text
  static const Color textLight = Color(0xFF9AB89A); // Light muted text

  // Card / surface borders
  static const Color cardBorder = Color(0xFFE8EDE8);
  static const Color selectedBg = Color(0xFFF0F7F4);
  static const Color tickerBg = Color(0xFFFAF8F2); // parchment strip

  static const double cardRadius = 20.0;
  static const double chipRadius = 14.0;
  static const double buttonRadius = 20.0;

  // Text Styles
  static TextStyle get headingLarge => GoogleFonts.playfairDisplay(
        fontSize: 28,
        fontWeight: FontWeight.w900,
        color: textDark,
        height: 1.2,
      );

  static TextStyle get headingMedium => GoogleFonts.playfairDisplay(
        fontSize: 22,
        fontWeight: FontWeight.w700,
        color: textDark,
      );

  static TextStyle get bodyLarge => GoogleFonts.dmSans(
        fontSize: 16,
        fontWeight: FontWeight.w500,
        color: textDark,
        height: 1.5,
      );

  static TextStyle get bodyMedium => GoogleFonts.dmSans(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        color: textMuted,
        height: 1.4,
      );

  static TextStyle get buttonText => GoogleFonts.dmSans(
        fontSize: 16,
        fontWeight: FontWeight.w700,
        color: Colors.white,
        letterSpacing: 0.5,
      );

  // Input Decoration
  static InputDecoration inputDecoration(String label, IconData icon) {
    return InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: textMuted),
      prefixIcon: Icon(icon, color: primaryGreen),
      filled: true,
      fillColor: Colors.transparent, // refined feel
      border: const UnderlineInputBorder(
        borderSide: BorderSide(color: Color(0xFFC8D8C8), width: 2),
      ),
      enabledBorder: const UnderlineInputBorder(
        borderSide: BorderSide(color: Color(0xFFC8D8C8), width: 2),
      ),
      focusedBorder: const UnderlineInputBorder(
        borderSide: BorderSide(color: primaryGreen, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 0, vertical: 16),
    );
  }

  // ThemeData
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: background,
      primaryColor: primaryGreen,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryGreen,
        surface: surface,
        primary: primaryGreen,
        secondary: secondaryGreen,
        error: error,
        brightness: Brightness.light,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: primaryGreen,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.playfairDisplay(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: Colors.white,
          fontStyle: FontStyle.italic,
        ),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0,
        shadowColor: const Color(0xFF1A4731).withOpacity(0.08),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(cardRadius),
          side: const BorderSide(color: Color(0xFFE8EDE8), width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      iconTheme: const IconThemeData(color: primaryGreen),
      dividerTheme: const DividerThemeData(
        color: Color(0xFFE8EDE8),
        thickness: 1,
        indent: 16,
        endIndent: 16,
      ),
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: FadeUpwardsCustomPageTransitionsBuilder(),
          TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
        },
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: background,
        contentTextStyle: GoogleFonts.dmSans(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          color: textDark,
        ),
        behavior: SnackBarBehavior.floating,
        shape: const Border(left: BorderSide(color: accentGold, width: 4)),
      ),
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(cardRadius)),
        ),
        dragHandleColor: accentGold,
        showDragHandle: true,
      ),
      splashColor: const Color(0x4DE9C46A), // gold rgba(233,196,106,0.3)
      highlightColor: const Color(0x26E9C46A),
    );
  }
}
