import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme.dart';
import 'language_screen.dart';
import 'phone_login_screen.dart';

/// Welcome Screen — First screen shown to unauthenticated users.
/// Asks whether the user is new or returning.
///  - New user → Language selection → Phone Login → Location → Farm Setup
///  - Returning user → Phone Login (auto-routes to Home after auth)
class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> with SingleTickerProviderStateMixin {
  late final AnimationController _spinCtrl;

  @override
  void initState() {
    super.initState();
    _spinCtrl = AnimationController(vsync: this, duration: const Duration(seconds: 6))..repeat();
  }

  @override
  void dispose() {
    _spinCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            colors: [
              Color(0xFF2D6A4F), // fresh leaf center
              Color(0xFF1A4731), // deep forest edges
            ],
            center: Alignment.center,
            radius: 1.2,
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 20),
            child: Column(
              children: [
                const Spacer(flex: 2),

                // ── Animated Logo with gold conic-gradient ring ──
                RotationTransition(
                  turns: _spinCtrl,
                  child: Container(
                    width: 110,
                    height: 110,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: const SweepGradient(
                        colors: [
                          Color(0xFFE9C46A),
                          Colors.transparent,
                          Color(0xFFE9C46A),
                          Colors.transparent,
                          Color(0xFFE9C46A),
                          Colors.transparent,
                        ],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.accentGold.withOpacity(0.35),
                          blurRadius: 30,
                          offset: const Offset(0, 8),
                        ),
                      ],
                    ),
                    child: Center(
                      child: Container(
                        width: 96,
                        height: 96,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [Color(0xFF2D6A4F), Color(0xFF40916C)],
                          ),
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.2),
                              blurRadius: 16,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                        child: const Icon(Icons.eco, color: Colors.white, size: 48),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 28),

                // ── Title — Playfair Display italic ──
                Text(
                  "KrishiMitra",
                  style: GoogleFonts.playfairDisplay(
                    fontSize: 34,
                    fontWeight: FontWeight.w900,
                    fontStyle: FontStyle.italic,
                    color: const Color(0xFFFFFBF0), // warm white
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  "Your Smart Farming Partner",
                  style: GoogleFonts.dmSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w500,
                    color: Colors.white70,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  "AI-powered insights for better crop decisions",
                  textAlign: TextAlign.center,
                  style: GoogleFonts.dmSans(
                    fontSize: 13,
                    color: Colors.white54,
                  ),
                ),

                const Spacer(flex: 2),

                // ── Feature highlights ──
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _buildFeatureChip(Icons.show_chart, "Price\nForecast"),
                    _buildFeatureChip(Icons.grass, "Yield\nPrediction"),
                    _buildFeatureChip(Icons.cloud, "Weather\nAlerts"),
                    _buildFeatureChip(Icons.recommend, "Sell/Hold\nAdvice"),
                  ],
                ),

                const Spacer(flex: 2),

                // ── New User Button ──
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const LanguageScreen()),
                      );
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.accentGold,
                      foregroundColor: AppTheme.textDark,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppTheme.buttonRadius),
                      ),
                      elevation: 4,
                      shadowColor: AppTheme.accentGold.withOpacity(0.4),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.person_add_outlined, size: 22),
                        const SizedBox(width: 10),
                        Text("I'm a New Farmer", style: GoogleFonts.dmSans(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.textDark,
                        )),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 14),

                // ── Returning User Button ──
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: OutlinedButton(
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const PhoneLoginScreen()),
                      );
                    },
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Colors.white38, width: 1.5),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppTheme.buttonRadius),
                      ),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.login, size: 22, color: Colors.white),
                        const SizedBox(width: 10),
                        Text(
                          "I'm a Returning Farmer",
                          style: GoogleFonts.dmSans(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                const Spacer(flex: 1),

                // ── Footer ──
                Text(
                  "Powered by AI  •  Made for Indian Farmers",
                  style: GoogleFonts.dmSans(
                    fontSize: 11,
                    color: Colors.white38,
                  ),
                ),
                const SizedBox(height: 8),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFeatureChip(IconData icon, String label) {
    return Column(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.12),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.white.withOpacity(0.08)),
          ),
          child: Icon(icon, color: AppTheme.accentGold, size: 24),
        ),
        const SizedBox(height: 6),
        Text(
          label,
          textAlign: TextAlign.center,
          style: GoogleFonts.dmSans(
            fontSize: 10,
            fontWeight: FontWeight.w500,
            color: Colors.white60,
            height: 1.2,
          ),
        ),
      ],
    );
  }
}
