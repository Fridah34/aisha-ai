import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { User, Mail, Briefcase, Eye, EyeOff } from 'lucide-react';

const EMAIL_REGEX = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

// we do not import location because signup page doesn't know where the user just came from

export default function Signup() {
    const navigate = useNavigate();
    const { signup, loading, error } = useAuth();
    
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        confirmPassword: '',
        business_name: '',
        business_type: '',
    });
    const [formError, setFormError] = useState(''); // Unified to match the visual card variables
    const [success, setSuccess] = useState('');
    const [emailWarning, setEmailWarning] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    // Update the state boxes in real-time as the user types
    const handleChange = (e) => {
        setFormData((prev) => ({
            ...prev,
            [e.target.name]: e.target.value,
        }));
        setFormError('');

        if (e.target.name === 'email') {
            setEmailWarning('');
        }
    };

    const handleEmailBlur = () => {
        const email = formData.email.trim().toLowerCase();
        const hasPlaceholderDomain = /@(example|test|fake)\.(com|net|org)$/i.test(email);

        if (!EMAIL_REGEX.test(email) || hasPlaceholderDomain) {
            setEmailWarning('Please enter a valid, real email address.');
            return;
        }

        setEmailWarning('');
    };

    // ======================================================
    // DYNAMIC PASSWORD STRENGTH CHECKER (OPTIONAL)
    // ======================================================
    const checkPasswordStrength = (password) => {
        if (!password) return { score: 0, text: '', color: 'bg-transparent', textColor: 'text-slate-400' };

        let score = 0;
        const hasKeyboardWalk = /qwerty|asdfgh|zxcvbn|12345/i.test(password);
        const hasRepeatingCharacters = /(.)\1\1\1/.test(password);

        if (password.length >=8) score++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
        if (/[0-9]/.test(password)) score++;
        if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;

        if (score === 4 && (hasKeyboardWalk || hasRepeatingCharacters)) {
            return { score: 2.5, text: 'Regular / Predictable Pattern', color: 'bg-orange-500 w-3/4', textColor: 'text-orange-400' };
        }

        if (password.length < 8 ||score <= 1) {
            return { score: 1, text: 'Weak Password', color: 'bg-red-500 w-1/3', textColor: 'text-red-400' };
        }
        if (score >=2 && score <= 3){
            return { score: 2, text: 'Good Password', color: 'bg-yellow-500 w-2/3', textColor: 'text-yellow-400' };
        }
        if (score >= 4) {
            return { score: 3, text: 'Strong Password', color: 'bg-green-500 w-full', textColor: 'text-green-400' };
        }
        return { score: 0, text: '', color: 'bg-transparent', textColor: 'text-slate-400' };
    };
    // ======================================================
    // FRONTEND SANITY CHECK (VALIDATION)
    // ======================================================
    const strength = checkPasswordStrength(formData.password);
    const validateForm = () => {
        if (!formData.name.trim()) return 'Name is required';
        if (!formData.email.trim()) return 'Email is required';
        if (!EMAIL_REGEX.test(formData.email.trim())) return 'Please enter a valid email address';
        if (!formData.business_name.trim()) return 'Business name is required';
        if (!formData.business_type) return 'Please select a business type';
        if (!formData.password) return 'Password is required';
        if (formData.password.length < 8) return 'Password must be at least 8 characters long';
        
        // Block weak and predictable passwords before submit
        if (strength.score < 3) {
            return 'Password is too predictable or weak. Please avoid keyboard rows, sequences, or repeating numbers.';
        }
        if (formData.password !== formData.confirmPassword) return 'Passwords do not match';
        return null;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setFormError('');
        setSuccess('');

        // Run the validation check before sending data to the backend
        const validationMessage = validateForm();
        if (validationMessage) {
            setFormError(validationMessage);
            return;
        }

        try {
            // Shaking hands perfectly with your FastAPI UserRegister schema
            const payload = {
                name: formData.name,
                email: formData.email.trim(),
                password: formData.password,
                confirm_password: formData.confirmPassword, // Matches your snake_case  schema
                business_name: formData.business_name,
                business_type: formData.business_type,
            };

            const result = await signup(payload);

            // Smart delay redirection logic branch
            if (result?.success) {
                setSuccess('Account created successfully! Redirecting to login...');
                setTimeout(() => {
                    navigate('/login', { replace: true, state: {
                        message: 'Account created! Please sign in.'
                    }, });
                }, 2000);
            }
        } catch (err) {
            setFormError(err.message || 'Registration failed. Please try again.');
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4 py-12">
            <div className="w-full max-w-md">
                
                {/* Header Block with the Glowing Orange Logo */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl mb-4 shadow-lg shadow-orange-500/10">
                        <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z" />
                        </svg>
                    </div>
                    <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">AISHA AI</h1>
                    <p className="text-slate-400 font-medium">Create Your Business Account</p>
                </div>

                {/* Main Interactive Form Body */}
                <div className="bg-slate-800 rounded-xl shadow-2xl border border-slate-700/60 p-8">
                    <h2 className="text-xl font-semibold text-white mb-6">Get Started</h2>

                    {/* ERROR BOX DISPLAY (Red) */}
                    {(formError || error) && (
                        <div className="mb-5 p-3.5 bg-red-900/30 border border-red-700/40 rounded-lg">
                            <p className="text-red-400 text-sm font-medium">{formError || error}</p>
                        </div>
                    )}

                    {/* SUCCESS BOX DISPLAY (Green) */}
                    {success && (
                        <div className="mb-5 p-3.5 bg-green-900/30 border border-green-700/40 rounded-lg">
                            <p className="text-green-400 text-sm font-medium">{success}</p>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {/* Field 1: Name */}
                        <div>
                            <label htmlFor="name" className="block text-sm font-medium text-slate-300 mb-1.5">Full Name</label>
                            <div className="relative flex items-center">
                                <User className="absolute right-3 w-5 h-5 text-slate-400 pointer-events-none" />
                                <input
                                    type="text" id="name" name="name" disabled={loading} value={formData.name} onChange={handleChange}
                                    className="w-full px-4 py-2.5 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                    placeholder="John Doe" required
                                />
                            </div>
                        </div>

                        {/* Field 2: Email */}
                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1.5">Email Address</label>
                            <div className="relative flex items-center">
                                <Mail className="absolute right-3 w-5 h-5 text-slate-400 pointer-events-none" />
                                <input
                                    type="email" id="email" name="email" disabled={loading} value={formData.email} onChange={handleChange}
                                    onBlur={handleEmailBlur}
                                    className="w-full px-4 py-2.5 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                    placeholder="you@example.com" required
                                />
                            </div>
                            {emailWarning && (
                                <p className="text-xs text-red-400 mt-1">{emailWarning}</p>
                            )}
                        </div>

                        {/* Field 3: Business Name */}
                        <div>
                            <label htmlFor="business_name" className="block text-sm font-medium text-slate-300 mb-1.5">Business Name</label>
                            <div className="relative flex items-center">
                                <Briefcase className="absolute right-3 w-5 h-5 text-slate-400 pointer-events-none" />
                                <input
                                    type="text" id="business_name" name="business_name" disabled={loading} value={formData.business_name} onChange={handleChange}
                                    className="w-full px-4 py-2.5 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                    placeholder="Your Business" required
                                />
                            </div>
                        </div>

                        {/* Field 4: Business Type */}
                        <div>
                            <label htmlFor="business_type" className="block text-sm font-medium text-slate-300 mb-1.5">Business Type</label>
                            <div className="relative flex items-center">
                                <select
                                    id="business_type" name="business_type" disabled={loading} 
                                    value={formData.business_type} onChange={handleChange}
                                    className="w-full px-4 py-2.5 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60 appearance-none"
                                    required
                                >
                                    <option value="" disabled> Select your business type</option>
                                    <option value="retail"> Retail</option>
                                    <option value="fashion"> Fashion</option>
                                    <option value="services"> Services</option>
                                    <option value="food"> Food</option>
                                </select>
                            </div>
                        </div>

                        {/* Field 4: Password */}
                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1.5">Password (min. 8 characters)</label>
                            <div className="relative flex items-center">
                                <input
                                    type={showPassword ? 'text' : 'password'} id="password" name="password" disabled={loading} value={formData.password} onChange={handleChange}
                                    className="w-full px-4 py-2.5 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                    placeholder="••••••••" required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword((prev) => !prev)}
                                    className="absolute right-3 text-slate-400 hover:text-slate-200 transition"
                                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                                >
                                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>

                            <p className="text-xs text-slate-400 mt-2">
                                Password must be at least 8 characters long and include an uppercase letter(A-Z), a lowercase letter(a-z), a number(0-9), and a special character(!@#$%^&*()-+).
                            </p>

                            <div className="mt-2">
                                <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                                    <div className={`h-full transition-all duration-300 ${strength.color}`}></div>
                                </div>
                                {formData.password && (
                                    <p className={`text-xs mt-1 font-medium ${strength.textColor}`}>{strength.text}</p>
                                )}
                            </div>
                        </div>

                        {/* Field 5: Confirm Password */}
                        <div>
                            <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300 mb-1.5">Confirm Password</label>
                            <div className="relative flex items-center">
                                <input
                                    type={showConfirmPassword ? 'text' : 'password'} id="confirmPassword" name="confirmPassword" disabled={loading} value={formData.confirmPassword} onChange={handleChange}
                                    className="w-full px-4 py-2.5 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                    placeholder="••••••••" required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmPassword((prev) => !prev)}
                                    className="absolute right-3 text-slate-400 hover:text-slate-200 transition"
                                    aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                                >
                                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>
                        </div>

                        {/* Submit Button */}
                        <button
                            type="submit" disabled={loading}
                            className="w-full flex items-center justify-center bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold py-2.5 rounded-lg hover:from-orange-600 hover:to-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500/50 transition disabled:opacity-50 mt-6"
                        >
                            {loading ? 'Creating Account...' : 'Create Account'}
                        </button>
                    </form>

                    {/* Aesthetic Row Divider */}
                    <div className="my-6 relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-slate-600/80"></div>
                        </div>
                        <div className="relative flex justify-center text-sm">
                            <span className="px-3 bg-slate-800 text-slate-400 font-medium">Already have an account?</span>
                        </div>
                    </div>

                    {/* Link back to login component view */}
                    <Link to="/login" className="block w-full text-center px-4 py-2.5 border border-slate-600 text-slate-300 font-semibold rounded-lg hover:bg-slate-700/40 hover:border-slate-500 transition">
                        Sign In
                    </Link>
                </div>
            </div>
        </div>
    );
}