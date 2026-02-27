import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/farmer_profile_provider.dart';
import '../../theme.dart';
import 'phone_login_screen.dart';

class LanguageScreen extends StatefulWidget {
  const LanguageScreen({super.key});

  @override
  State<LanguageScreen> createState() => _LanguageScreenState();
}

class _LanguageScreenState extends State<LanguageScreen>
    with SingleTickerProviderStateMixin {
  String? _selected;
  late AnimationController _animCtrl;
  late Animation<double> _fadeAnim;

  final List<Map<String, String>> _languages = [
    {'code': 'en', 'label': 'English', 'native': 'English', 'emoji': '🇬🇧'},
    {'code': 'hi', 'label': 'Hindi', 'native': 'हिन्दी', 'emoji': '🇮🇳'},
    {'code': 'mr', 'label': 'Marathi', 'native': 'मराठी', 'emoji': '🏛️'},
    {'code': 'te', 'label': 'Telugu', 'native': 'తెలుగు', 'emoji': '🌾'},
    {'code': 'ta', 'label': 'Tamil', 'native': 'தமிழ்', 'emoji': '🪷'},
    {'code': 'kn', 'label': 'Kannada', 'native': 'ಕನ್ನಡ', 'emoji': '🌿'},
    {'code': 'pa', 'label': 'Punjabi', 'native': 'ਪੰਜਾਬੀ', 'emoji': '🌻'},
    {'code': 'gu', 'label': 'Gujarati', 'native': 'ગુજરાતી', 'emoji': '🏖️'},
    {'code': 'bn', 'label': 'Bengali', 'native': 'বাংলা', 'emoji': '🎭'},
    {'code': 'od', 'label': 'Odia', 'native': 'ଓଡ଼ିଆ', 'emoji': '🛕'},
  ];

  @override
  void initState() {
    super.initState();
    _animCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _fadeAnim = CurvedAnimation(parent: _animCtrl, curve: Curves.easeOut);
    _animCtrl.forward();
  }

  @override
  void dispose() {
    _animCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surface, // changed to surface (warm cream)
      body: SafeArea(
        child: FadeTransition(
          opacity: _fadeAnim,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 24),

                // ── App Logo ──
                Container(
                  width: 72,
                  height: 72,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [AppTheme.primaryGreen, AppTheme.secondaryGreen],
                    ),
                    borderRadius: BorderRadius.circular(18),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.primaryGreen.withOpacity(0.3),
                        blurRadius: 16,
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: const Icon(Icons.eco, color: Colors.white, size: 36),
                ),
                const SizedBox(height: 20),

                // ── Header ──
                Text(
                  "Welcome to KrishiMitra 🙏",
                  style: AppTheme.headingLarge.copyWith(fontSize: 26),
                ),
                const SizedBox(height: 6),
                Text(
                  "Choose your language",
                  style: AppTheme.bodyLarge.copyWith(
                    color: AppTheme.textLight,
                    fontSize: 15,
                  ),
                ),
                Text(
                  "अपनी भाषा चुनें",
                  style: AppTheme.bodyMedium.copyWith(
                    color: AppTheme.textLight,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 24),

                // ── Language Grid ──
                Expanded(
                  child: GridView.builder(
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      mainAxisSpacing: 10,
                      crossAxisSpacing: 10,
                      childAspectRatio: 1.8,
                    ),
                    itemCount: _languages.length,
                    itemBuilder: (context, index) {
                      final lang = _languages[index];
                      final isSelected = _selected == lang['code'];
                      return GestureDetector(
                        onTap: () => setState(() => _selected = lang['code']),
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? const Color(0xFFFDF3DC) // warm glow parchment
                                : Colors.white, // default parchment card
                            borderRadius:
                                BorderRadius.circular(AppTheme.cardRadius),
                            border: Border.all(
                              color: isSelected
                                  ? AppTheme.accentGold
                                  : Colors.grey.shade300,
                              width: isSelected ? 2 : 1,
                            ),
                            boxShadow: isSelected
                                ? [
                                    BoxShadow(
                                      color: AppTheme.accentGold
                                          .withOpacity(0.3),
                                      blurRadius: 12,
                                      offset: const Offset(0, 4),
                                    )
                                  ]
                                : [],
                          ),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 8),
                            child: Row(
                              children: [
                                Text(lang['emoji'] ?? '',
                                    style: const TextStyle(fontSize: 22)),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Text(
                                        lang['native'] ?? '',
                                        style: TextStyle(
                                          fontSize: 14,
                                          fontWeight: FontWeight.w600,
                                          color: isSelected
                                              ? AppTheme.primaryGreen
                                              : AppTheme.textDark,
                                        ),
                                      ),
                                      Text(
                                        lang['label'] ?? '',
                                        style: TextStyle(
                                          fontSize: 11,
                                          color: isSelected
                                              ? AppTheme.primaryGreen.withOpacity(0.8)
                                              : AppTheme.textLight,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                if (isSelected)
                                  const Icon(Icons.check_circle,
                                      color: AppTheme.accentGold, size: 20),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),

                // ── Continue Button ──
                const SizedBox(height: 12),
                AnimatedOpacity(
                  opacity: _selected != null ? 1.0 : 0.4,
                  duration: const Duration(milliseconds: 300),
                  child: SizedBox(
                    height: 52,
                    child: ElevatedButton(
                      onPressed: _selected != null ? _onContinue : null,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryGreen,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius:
                              BorderRadius.circular(AppTheme.buttonRadius),
                        ),
                        elevation: 2,
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text("Continue", style: AppTheme.buttonText),
                          const SizedBox(width: 8),
                          const Icon(Icons.arrow_forward, size: 20),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _onContinue() async {
    if (_selected == null) return;
    final profile = Provider.of<FarmerProfile>(context, listen: false);
    await profile.setLanguage(_selected!);

    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const PhoneLoginScreen()),
      );
    }
  }
}
