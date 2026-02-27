import 'package:flutter/material.dart';
import '../../theme.dart';
import 'language_screen.dart';
import 'phone_login_screen.dart';

/// Welcome Screen — First screen shown to unauthenticated users.
/// Asks whether the user is new or returning.
///  - New user → Language selection → Phone Login → Location → Farm Setup
///  - Returning user → Phone Login (auto-routes to Home after auth)
class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 20),
          child: Column(
            children: [
              const Spacer(flex: 2),

              // ── Logo ──
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [AppTheme.primaryGreen, AppTheme.secondaryGreen],
                  ),
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.primaryGreen.withOpacity(0.3),
                      blurRadius: 24,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: const Icon(Icons.eco, color: Colors.white, size: 52),
              ),
              const SizedBox(height: 28),

              // ── Title ──
              Text(
                "KrishiMitra",
                style: AppTheme.headingLarge.copyWith(fontSize: 32),
              ),
              const SizedBox(height: 6),
              Text(
                "Your Smart Farming Partner",
                style: AppTheme.bodyMedium.copyWith(
                  fontSize: 15,
                  color: Colors.grey.shade600,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                "AI-powered insights for better crop decisions",
                textAlign: TextAlign.center,
                style: AppTheme.bodyMedium.copyWith(
                  fontSize: 13,
                  color: Colors.grey.shade500,
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
                    backgroundColor: AppTheme.primaryGreen,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppTheme.buttonRadius),
                    ),
                    elevation: 2,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.person_add_outlined, size: 22),
                      const SizedBox(width: 10),
                      Text("I'm a New Farmer", style: AppTheme.buttonText),
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
                    foregroundColor: AppTheme.primaryGreen,
                    side: const BorderSide(color: AppTheme.primaryGreen, width: 1.5),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppTheme.buttonRadius),
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.login, size: 22),
                      const SizedBox(width: 10),
                      Text(
                        "I'm a Returning Farmer",
                        style: AppTheme.buttonText.copyWith(
                          color: AppTheme.primaryGreen,
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
                style: AppTheme.bodyMedium.copyWith(
                  fontSize: 11,
                  color: Colors.grey.shade400,
                ),
              ),
              const SizedBox(height: 8),
            ],
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
            color: AppTheme.lightGreen,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: AppTheme.primaryGreen, size: 24),
        ),
        const SizedBox(height: 6),
        Text(
          label,
          textAlign: TextAlign.center,
          style: AppTheme.bodyMedium.copyWith(
            fontSize: 10,
            fontWeight: FontWeight.w500,
            color: AppTheme.textLight,
            height: 1.2,
          ),
        ),
      ],
    );
  }
}
