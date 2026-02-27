import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../theme.dart';

class PestVisionScreen extends StatefulWidget {
  final String currentCrop;

  const PestVisionScreen({super.key, required this.currentCrop});

  @override
  State<PestVisionScreen> createState() => _PestVisionScreenState();
}

class _PestVisionScreenState extends State<PestVisionScreen> {
  XFile? _image;
  bool _isAnalyzing = false;
  Map<String, dynamic>? _result;
  final ImagePicker _picker = ImagePicker();

  Future<void> _pickImage(ImageSource source) async {
    debugPrint("Picking image from $source...");
    try {
      final XFile? selected = await _picker.pickImage(
        source: source,
        imageQuality: 50,
        maxWidth: 1024,
      );

      if (selected != null) {
        debugPrint("Image selected: ${selected.path}");
        setState(() {
          _image = selected;
          _result = null;
        });
        _analyzeImage();
      } else {
        debugPrint("No image selected.");
      }
    } catch (e) {
      debugPrint("Error picking image: $e");
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Could not open ${source.name}: $e")),
        );
      }
    }
  }

  Future<void> _analyzeImage() async {
    if (_image == null) return;

    setState(() {
      _isAnalyzing = true;
    });

    try {
      final bytes = await _image!.readAsBytes();
      final base64Image = base64Encode(bytes);

      final api = Provider.of<ApiService>(context, listen: false);
      final response = await api.analyzePest(base64Image, widget.currentCrop);

      setState(() {
        _result = response;
        _isAnalyzing = false;
      });
    } catch (e) {
      setState(() {
        _isAnalyzing = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Analysis failed: $e")),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text("AI Pest & Disease Scan"),
        elevation: 0,
        backgroundColor: Colors.white,
        foregroundColor: AppTheme.textDark,
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            _buildHeader(),
            const SizedBox(height: 20),
            _buildImageSlot(),
            const SizedBox(height: 24),
            _buildActionButtonsInline(), // Moved buttons here for better reliability
            const SizedBox(height: 24),
            if (_isAnalyzing) _buildAnalyzingState(),
            if (_result != null) _buildResultCard(),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButtonsInline() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        children: [
          Expanded(
            child: ElevatedButton.icon(
              onPressed: () => _pickImage(ImageSource.gallery),
              icon: const Icon(Icons.photo_library),
              label: const Text("Gallery"),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: AppTheme.textDark,
                side: const BorderSide(color: Color(0xFFE0E0E0)),
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: ElevatedButton.icon(
              onPressed: () => _pickImage(kIsWeb ? ImageSource.gallery : ImageSource.camera),
              icon: Icon(kIsWeb ? Icons.upload_file : Icons.camera_alt),
              label: Text(kIsWeb ? "Upload" : "Camera"),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryGreen,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      color: Colors.white,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "Detect Pests Early",
            style: GoogleFonts.dmSans(
              fontSize: 24,
              fontWeight: FontWeight.w800,
              color: AppTheme.textDark,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            "Scan a leaf to protect your ${widget.currentCrop} crop and see how it affects market prices.",
            style: GoogleFonts.dmSans(
              fontSize: 14,
              color: AppTheme.textLight,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildImageSlot() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 24),
      height: 280,
      width: double.infinity,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFFEEEEEE)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: _image == null
            ? Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.add_a_photo_outlined,
                      size: 64, color: const Color(0xFFE0E0E0)),
                  const SizedBox(height: 16),
                  Text(
                    "No leaf photo scanned",
                    style: GoogleFonts.dmSans(
                        color: Colors.grey, fontWeight: FontWeight.w600),
                  ),
                ],
              )
            : kIsWeb
                ? Image.network(_image!.path, fit: BoxFit.cover)
                : Image.file(File(_image!.path), fit: BoxFit.cover),
      ),
    );
  }

  Widget _buildAnalyzingState() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          const CircularProgressIndicator(color: AppTheme.primaryGreen),
          const SizedBox(height: 16),
          Text(
            "KrishiMitra AI is analyzing your leaf...",
            style: GoogleFonts.dmSans(
                fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
          ),
          Text(
            "Identifying pests & calculating market risk",
            style: GoogleFonts.dmSans(fontSize: 12, color: AppTheme.textLight),
          ),
        ],
      ),
    );
  }

  Widget _buildResultCard() {
    final res = _result!;
    final color = res['severity_color'] == 'red'
        ? AppTheme.error
        : res['severity_color'] == 'orange'
            ? AppTheme.accentOrange
            : AppTheme.primaryGreen;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 24),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: color.withOpacity(0.2), width: 2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                child: const Icon(Icons.auto_awesome,
                    color: Colors.white, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      res['condition'] ?? "Unknown Condition",
                      style: GoogleFonts.dmSans(
                        fontSize: 20,
                        fontWeight: FontWeight.w900,
                        color: color,
                      ),
                    ),
                    Text(
                      "Certainty: ${res['confidence'] ?? 'N/A'}",
                      style: GoogleFonts.dmSans(
                          fontSize: 12,
                          color: color,
                          fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),

          _resultItem("What we see:", res['findings'] ?? ""),
          const SizedBox(height: 16),
          _resultItem("Farmer Action:", res['treatment'] ?? ""),

          const Divider(height: 32),

          // MARKET RISK BLOCK - THE USP
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              children: [
                Icon(Icons.trending_up, color: color),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "MARKET PRICE RISK",
                        style: GoogleFonts.dmSans(
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.textLight),
                      ),
                      Text(
                        "${res['market_risk_impact'] ?? 'LOW'} IMPACT",
                        style: GoogleFonts.dmSans(
                            fontSize: 18,
                            fontWeight: FontWeight.w900,
                            color: AppTheme.textDark),
                      ),
                      Text(
                        "If this spreads locally, regional prices may rise due to supply shortage.",
                        style: GoogleFonts.dmSans(
                            fontSize: 11, color: AppTheme.textLight),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _resultItem(String title, String content) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title,
            style: GoogleFonts.dmSans(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: AppTheme.textLight)),
        const SizedBox(height: 4),
        Text(content,
            style: GoogleFonts.dmSans(
                fontSize: 15, color: AppTheme.textDark, height: 1.4)),
      ],
    );
  }
}
