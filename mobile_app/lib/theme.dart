import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Colors - Dark Green, Clean & Sharp
  static const Color primaryGreen = Color(0xFF1B5E20); // Deep Forest Green
  static const Color secondaryGreen = Color(0xFF2E7D32); // Dark Emerald
  static const Color lightGreen = Color(0xFFE8F5E9); // Soft green tint for backgrounds
  static const Color background = Color(0xFFF5F5F5); // Neutral grey-white
  static const Color surface = Colors.white;
  static const Color error = Color(0xFFD32F2F); // Strong Red

  static const Color textDark = Color(0xFF1A1A1A); // Near black
  static const Color textLight = Color(0xFF616161);

  // Accent Colors
  static const Color accentBlue = Color(0xFF1565C0);
  static const Color accentOrange = Color(0xFFE65100);
  static const Color accentPurple = Color(0xFF4A148C);
  static const Color accentTeal = Color(0xFF00796B);

  // Sharp radius — zero or minimal for clean edges
  static const double cardRadius = 4.0;
  static const double buttonRadius = 4.0;
  static const double inputRadius = 4.0;
  static const double chipRadius = 4.0;

  // Text Styles
  static TextStyle get headingLarge => GoogleFonts.poppins(
        fontSize: 28,
        fontWeight: FontWeight.bold,
        color: textDark,
        height: 1.2,
      );

  static TextStyle get headingMedium => GoogleFonts.poppins(
        fontSize: 22,
        fontWeight: FontWeight.w600,
        color: textDark,
      );

  static TextStyle get bodyLarge => GoogleFonts.inter(
        fontSize: 16,
        color: textDark,
        height: 1.5,
      );

  static TextStyle get bodyMedium => GoogleFonts.inter(
        fontSize: 14,
        color: textLight,
        height: 1.4,
      );

  static TextStyle get buttonText => GoogleFonts.poppins(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: Colors.white,
        letterSpacing: 0.5,
      );

  // Input Decoration
  static InputDecoration inputDecoration(String label, IconData icon) {
    return InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: textLight),
      prefixIcon: Icon(icon, color: primaryGreen),
      filled: true,
      fillColor: surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(inputRadius),
        borderSide: BorderSide.none,
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(inputRadius),
        borderSide: BorderSide(color: Colors.grey.shade300),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(inputRadius),
        borderSide: const BorderSide(color: primaryGreen, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
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
        titleTextStyle: GoogleFonts.poppins(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: Colors.white,
        ),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 1,
        shadowColor: Colors.black.withOpacity(0.08),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(cardRadius)),
        margin: EdgeInsets.zero,
      ),
      iconTheme: const IconThemeData(color: primaryGreen),
    );
  }
}
