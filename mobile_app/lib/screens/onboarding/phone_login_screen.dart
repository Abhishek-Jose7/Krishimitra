import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import '../../providers/farmer_profile_provider.dart';
import '../../services/api_service.dart';
import '../../theme.dart';
import 'location_screen.dart';

class PhoneLoginScreen extends StatefulWidget {
  const PhoneLoginScreen({super.key});

  @override
  State<PhoneLoginScreen> createState() => _PhoneLoginScreenState();
}

class _PhoneLoginScreenState extends State<PhoneLoginScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // Shared
  final _phoneController = TextEditingController();
  bool _isLoading = false;
  String? _error;

  // OTP tab
  final _otpController = TextEditingController();
  bool _otpSent = false;
  String? _devOtp;

  // Password tab
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  bool _isRegistering = false; // false = login, true = register
  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (_tabController.indexIsChanging) {
        setState(() => _error = null);
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _phoneController.dispose();
    _otpController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  // ── OTP Flow ──────────────────────────────────────────────
  Future<void> _sendOtp() async {
    final phone = _phoneController.text.trim();
    if (phone.length < 10) {
      setState(() => _error = "Enter a valid 10-digit phone number");
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await http.post(
        Uri.parse('${ApiService.baseUrl}/auth/send-otp'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'phone': phone}),
      );

      final data = json.decode(response.body);
      if (response.statusCode == 200 && data['success'] == true) {
        setState(() {
          _otpSent = true;
          _devOtp = data['dev_otp'];
        });
      } else {
        setState(() => _error = data['error'] ?? 'Failed to send OTP');
      }
    } catch (e) {
      setState(() => _error = 'Network error. Please try again.');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _verifyOtp() async {
    final phone = _phoneController.text.trim();
    final otp = _otpController.text.trim();

    if (otp.length < 6) {
      setState(() => _error = "Enter the 6-digit OTP");
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await http.post(
        Uri.parse('${ApiService.baseUrl}/auth/verify-otp'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'phone': phone, 'otp': otp}),
      );

      final data = json.decode(response.body);
      if (response.statusCode == 200 && data['success'] == true) {
        await _onAuthSuccess(data, phone);
      } else {
        setState(() => _error = data['error'] ?? 'Invalid OTP');
      }
    } catch (e) {
      setState(() => _error = 'Network error. Please try again.');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // ── Password Flow ─────────────────────────────────────────
  Future<void> _loginWithPassword() async {
    final phone = _phoneController.text.trim();
    final password = _passwordController.text.trim();

    if (phone.length < 10) {
      setState(() => _error = "Enter a valid 10-digit phone number");
      return;
    }
    if (password.length < 6) {
      setState(() => _error = "Password must be at least 6 characters");
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final api = Provider.of<ApiService>(context, listen: false);

      Map<String, dynamic> data;
      if (_isRegistering) {
        data = await api.registerWithPassword(
          phone: phone,
          password: password,
          name: _nameController.text.trim().isNotEmpty
              ? _nameController.text.trim()
              : null,
        );
      } else {
        data = await api.loginWithPassword(
          phone: phone,
          password: password,
        );
      }

      if (data['success'] == true) {
        await _onAuthSuccess(data, phone);
      } else {
        setState(() => _error = data['error'] ?? 'Authentication failed');
      }
    } catch (e) {
      final msg = e.toString().replaceFirst('Exception: ', '');
      setState(() => _error = msg.contains('Exception:')
          ? msg.replaceFirst('Exception: ', '')
          : msg);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // ── Shared success handler ────────────────────────────────
  Future<void> _onAuthSuccess(Map<String, dynamic> data, String phone) async {
    final profile = Provider.of<FarmerProfile>(context, listen: false);
    await profile.setAuth(
      tkn: data['token'],
      id: data['farmer_id'],
      ph: phone,
    );

    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const LocationScreen()),
      );
    }
  }

  // ── BUILD ─────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 40),

              // ── Logo ──
              Center(
                child: Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [AppTheme.primaryGreen, AppTheme.secondaryGreen],
                    ),
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.primaryGreen.withOpacity(0.25),
                        blurRadius: 20,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: const Icon(Icons.eco, color: Colors.white, size: 40),
                ),
              ),
              const SizedBox(height: 20),

              Center(
                child: Text(
                  "Welcome to KrishiMitra",
                  style: AppTheme.headingLarge.copyWith(fontSize: 22),
                ),
              ),
              const SizedBox(height: 4),
              Center(
                child: Text(
                  "Login or create your account",
                  style: AppTheme.bodyMedium.copyWith(
                    fontSize: 14,
                    color: Colors.grey.shade600,
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // ── Tab Bar ──
              Container(
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(12),
                ),
                padding: const EdgeInsets.all(4),
                child: TabBar(
                  controller: _tabController,
                  indicator: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(10),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.06),
                        blurRadius: 6,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  indicatorSize: TabBarIndicatorSize.tab,
                  labelColor: AppTheme.primaryGreen,
                  unselectedLabelColor: Colors.grey.shade500,
                  labelStyle: AppTheme.headingMedium.copyWith(fontSize: 14),
                  unselectedLabelStyle:
                      AppTheme.bodyMedium.copyWith(fontSize: 14),
                  dividerHeight: 0,
                  tabs: const [
                    Tab(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.sms_outlined, size: 18),
                          SizedBox(width: 6),
                          Text("OTP Login"),
                        ],
                      ),
                    ),
                    Tab(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.lock_outline, size: 18),
                          SizedBox(width: 6),
                          Text("Password"),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // ── Tab Content ──
              SizedBox(
                // Use a fixed height that accommodates both tabs
                height: 380,
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildOtpTab(),
                    _buildPasswordTab(),
                  ],
                ),
              ),

              // ── Footer ──
              Text(
                "By continuing, you agree to our Terms of Service",
                textAlign: TextAlign.center,
                style: AppTheme.bodyMedium.copyWith(
                  fontSize: 11,
                  color: Colors.grey,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── OTP Tab ───────────────────────────────────────────────
  Widget _buildOtpTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (!_otpSent) ...[
          Text(
            "Enter Phone Number",
            style: AppTheme.headingMedium.copyWith(fontSize: 16),
          ),
          const SizedBox(height: 4),
          Text(
            "We'll send you a 6-digit verification code",
            style: AppTheme.bodyMedium.copyWith(
                fontSize: 13, color: Colors.grey.shade600),
          ),
          const SizedBox(height: 16),
          _buildPhoneInput(),
        ],

        if (_otpSent) ...[
          Text(
            "Enter OTP",
            style: AppTheme.headingMedium.copyWith(fontSize: 16),
          ),
          const SizedBox(height: 4),
          Text(
            "Sent to +91 ${_phoneController.text.trim()}",
            style: AppTheme.bodyMedium.copyWith(
                fontSize: 13, color: Colors.grey.shade600),
          ),
          const SizedBox(height: 16),
          _buildOtpInput(),
          if (_devOtp != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppTheme.lightGreen,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.developer_mode,
                      color: AppTheme.primaryGreen, size: 16),
                  const SizedBox(width: 8),
                  Text(
                    "Dev OTP: $_devOtp",
                    style: AppTheme.bodyMedium.copyWith(
                      color: AppTheme.primaryGreen,
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 8),
          Center(
            child: TextButton(
              onPressed: _isLoading
                  ? null
                  : () {
                      setState(() {
                        _otpSent = false;
                        _otpController.clear();
                        _devOtp = null;
                      });
                    },
              child: Text(
                "Change Number",
                style: AppTheme.bodyMedium.copyWith(
                  color: AppTheme.primaryGreen,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],

        if (_error != null && _tabController.index == 0) ...[
          const SizedBox(height: 8),
          _buildErrorBox(_error!),
        ],

        const SizedBox(height: 16),

        _buildActionButton(
          label: _otpSent ? "Verify & Continue" : "Send OTP",
          icon: _otpSent ? Icons.check : Icons.send,
          onPressed: _otpSent ? _verifyOtp : _sendOtp,
        ),
      ],
    );
  }

  // ── Password Tab ──────────────────────────────────────────
  Widget _buildPasswordTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          _isRegistering ? "Create Account" : "Login with Password",
          style: AppTheme.headingMedium.copyWith(fontSize: 16),
        ),
        const SizedBox(height: 4),
        Text(
          _isRegistering
              ? "Register with your phone number"
              : "Enter your phone and password",
          style: AppTheme.bodyMedium.copyWith(
              fontSize: 13, color: Colors.grey.shade600),
        ),
        const SizedBox(height: 16),

        // Phone
        _buildPhoneInput(),
        const SizedBox(height: 12),

        // Name (register only)
        if (_isRegistering) ...[
          TextField(
            controller: _nameController,
            style: AppTheme.bodyMedium.copyWith(fontSize: 16),
            decoration: InputDecoration(
              hintText: "Your name (optional)",
              prefixIcon:
                  const Icon(Icons.person_outline, color: Colors.grey),
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppTheme.inputRadius),
                borderSide: BorderSide(color: Colors.grey.shade300),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppTheme.inputRadius),
                borderSide:
                    const BorderSide(color: AppTheme.primaryGreen, width: 2),
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],

        // Password
        TextField(
          controller: _passwordController,
          obscureText: _obscurePassword,
          style: AppTheme.bodyMedium.copyWith(fontSize: 16),
          decoration: InputDecoration(
            hintText: "Password (min 6 chars)",
            prefixIcon: const Icon(Icons.lock_outline, color: Colors.grey),
            suffixIcon: IconButton(
              icon: Icon(
                _obscurePassword ? Icons.visibility_off : Icons.visibility,
                color: Colors.grey,
              ),
              onPressed: () =>
                  setState(() => _obscurePassword = !_obscurePassword),
            ),
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppTheme.inputRadius),
              borderSide: BorderSide(color: Colors.grey.shade300),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppTheme.inputRadius),
              borderSide:
                  const BorderSide(color: AppTheme.primaryGreen, width: 2),
            ),
          ),
        ),

        if (_error != null && _tabController.index == 1) ...[
          const SizedBox(height: 8),
          _buildErrorBox(_error!),
        ],

        const SizedBox(height: 16),

        _buildActionButton(
          label: _isRegistering ? "Register" : "Login",
          icon: _isRegistering ? Icons.person_add : Icons.login,
          onPressed: _loginWithPassword,
        ),

        const SizedBox(height: 8),
        Center(
          child: TextButton(
            onPressed: () {
              setState(() {
                _isRegistering = !_isRegistering;
                _error = null;
              });
            },
            child: Text(
              _isRegistering
                  ? "Already have an account? Login"
                  : "New user? Register here",
              style: AppTheme.bodyMedium.copyWith(
                color: AppTheme.primaryGreen,
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
            ),
          ),
        ),
      ],
    );
  }

  // ── Shared Widgets ────────────────────────────────────────
  Widget _buildPhoneInput() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppTheme.inputRadius),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Row(
        children: [
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
            decoration: BoxDecoration(
              color: Colors.grey.shade50,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(AppTheme.inputRadius),
                bottomLeft: Radius.circular(AppTheme.inputRadius),
              ),
            ),
            child: Text(
              "+91",
              style: AppTheme.headingMedium.copyWith(fontSize: 16),
            ),
          ),
          Container(width: 1, height: 30, color: Colors.grey.shade300),
          Expanded(
            child: TextField(
              controller: _phoneController,
              keyboardType: TextInputType.phone,
              maxLength: 10,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              style: AppTheme.headingMedium.copyWith(fontSize: 18),
              decoration: const InputDecoration(
                hintText: "9876543210",
                border: InputBorder.none,
                counterText: "",
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 14, vertical: 16),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOtpInput() {
    return TextField(
      controller: _otpController,
      keyboardType: TextInputType.number,
      maxLength: 6,
      textAlign: TextAlign.center,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      style: AppTheme.headingLarge.copyWith(fontSize: 32, letterSpacing: 12),
      decoration: InputDecoration(
        hintText: "• • • • • •",
        hintStyle: TextStyle(
          color: Colors.grey.shade400,
          fontSize: 28,
          letterSpacing: 8,
        ),
        counterText: "",
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTheme.inputRadius),
          borderSide: BorderSide(color: Colors.grey.shade300),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTheme.inputRadius),
          borderSide: const BorderSide(color: AppTheme.primaryGreen, width: 2),
        ),
      ),
    );
  }

  Widget _buildErrorBox(String message) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.error.withOpacity(0.08),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppTheme.error, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: AppTheme.bodyMedium.copyWith(
                color: AppTheme.error,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton({
    required String label,
    required IconData icon,
    required VoidCallback onPressed,
  }) {
    return SizedBox(
      height: 52,
      child: ElevatedButton(
        onPressed: _isLoading ? null : onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppTheme.primaryGreen,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTheme.buttonRadius),
          ),
          elevation: 2,
        ),
        child: _isLoading
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(label, style: AppTheme.buttonText),
                  const SizedBox(width: 8),
                  Icon(icon, size: 20),
                ],
              ),
      ),
    );
  }
}
