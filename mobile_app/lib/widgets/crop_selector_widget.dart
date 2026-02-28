import 'package:flutter/material.dart';

import '../theme.dart';

/// Reusable horizontal crop selector matching the "Nearby Mandi Prices" style:
/// rounded pill buttons, light background for inactive, dark green for active,
/// emoji at left, text at right. Same spacing, padding, font weight, height.
class CropSelectorWidget extends StatelessWidget {
  final List<String> crops;
  final String selectedCrop;
  final ValueChanged<String> onCropSelected;

  const CropSelectorWidget({
    super.key,
    required this.crops,
    required this.selectedCrop,
    required this.onCropSelected,
  });

  static const Map<String, String> cropEmojis = {
    'Rice': '🌾',
    'Wheat': '🌿',
    'Maize': '🌽',
    'Soybean': '🫘',
    'Cotton': '☁️',
    'Sugarcane': '🎋',
    'Groundnut': '🥜',
    'Onion': '🧅',
    'Tomato': '🍅',
    'Potato': '🥔',
    'Coconut': '🥥',
    'Ragi': '🌾',
    'Jowar': '🌾',
    'Bajra': '🌾',
    'Mustard': '🌻',
    'Gram': '🫘',
    'Chickpea': '🌱',
    'Lentils': '🫘',
    'Arecanut': '🌴',
    'Sunflower': '🌻',
    'Banana': '🍌',
    'Chilli': '🌶️',
    'Turmeric': '🌿',
    'Cumin': '🌿',
    'Pepper': '🌶️',
    'Cardamom': '🌿',
    'Mango': '🥭',
    'Grapes': '🍇',
  };

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 64,
      color: AppTheme.surface,
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        itemCount: crops.length,
        itemBuilder: (context, index) {
          final crop = crops[index];
          final isSelected = crop == selectedCrop;
          return GestureDetector(
            onTap: () => onCropSelected(crop),
            child: Container(
              margin: const EdgeInsets.only(right: 10),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: isSelected
                    ? AppTheme.primaryGreen
                    : AppTheme.background,
                borderRadius: BorderRadius.circular(AppTheme.chipRadius),
                border: Border.all(
                  color: isSelected
                      ? AppTheme.primaryGreen
                      : Colors.grey.shade300,
                  width: isSelected ? 2 : 1,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    cropEmojis[crop] ?? '🌱',
                    style: const TextStyle(fontSize: 18),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    crop,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: isSelected
                          ? Colors.white
                          : AppTheme.textDark,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
