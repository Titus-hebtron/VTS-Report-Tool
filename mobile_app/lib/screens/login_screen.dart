import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  String _contractor = 'Wizpro';
  String _username = '';
  String _password = '';
  bool _isLoading = false;

  final List<String> _contractors = ['Wizpro', 'Paschal', 'RE Office', 'Avators'];

  void _submit() async {
    if (_formKey.currentState!.validate()) {
      setState(() => _isLoading = true);
      try {
        await Provider.of<AuthProvider>(context, listen: false)
            .login(_contractor, _username, _password);
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Login failed: $e')),
        );
      } finally {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('VTS Report Tool Login')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              DropdownButtonFormField<String>(
                value: _contractor,
                items: _contractors.map((contractor) {
                  return DropdownMenuItem(
                    value: contractor,
                    child: Text(contractor),
                  );
                }).toList(),
                onChanged: (value) => setState(() => _contractor = value!),
                decoration: const InputDecoration(labelText: 'Contractor'),
              ),
              TextFormField(
                decoration: const InputDecoration(labelText: 'Username'),
                validator: (value) => value!.isEmpty ? 'Enter username' : null,
                onChanged: (value) => _username = value,
              ),
              TextFormField(
                decoration: const InputDecoration(labelText: 'Password'),
                obscureText: true,
                validator: (value) => value!.isEmpty ? 'Enter password' : null,
                onChanged: (value) => _password = value,
              ),
              const SizedBox(height: 20),
              _isLoading
                  ? const CircularProgressIndicator()
                  : ElevatedButton(
                      onPressed: _submit,
                      child: const Text('Login'),
                    ),
            ],
          ),
        ),
      ),
    );
  }
}