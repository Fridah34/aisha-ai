import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

// we do not import location because signup page doesnt know where the user just came from

export default function Signup() {
    const navigate = useNavigate();
    const { signup, loading, error } = useAuth();
    
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        confirmPassword: '',
        business_name: '',
    });
    const [formError, setFormError] = useState(''); // Unified to match the visual card variables
    const [success, setSuccess] = useState('');

    // Update the state boxes in real-time as the user types
    const handleChange = (e) => {
        setFormData((prev) => ({
            ...prev,
            [e.target.name]: e.target.value,
        }));
        setFormError('');
    };

    // ======================================================
    // FRONTEND SANITY CHECK (VALIDATION)
    // ======================================================
    const validateForm = () => {
        if (!formData.name.trim()) return 'Name is required';
        if (!formData.email.trim()) return 'Email is required';
        if (!formData.business_name.trim()) return 'Business name is required';
        if (!formData.password) return 'Password is required';
        if (formData.password.length < 8) return 'Password must be at least 8 characters long';
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
            const result = await signup({
                name: formData.name,
                email: formData.email,
                password: formData.password,
                confirm_password: formData.confirmPassword, // Matches your snake_case Pydantic schema
                business_name: formData.business_name,
            });

            // Smart delay redirection logic branch
            if (result?.success && localStorage.getItem('accessToken')) {
                setSuccess('Account created successfully! Logging you in...');
                setTimeout(() => {
                    navigate('/overview');
                }, 1000);
            } else {
                setSuccess('Account created successfully! Redirecting to login...');
                setTimeout(() => {
                    navigate('/login');
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
                            <input
                                type="text" id="name" name="name" disabled={loading} value={formData.name} onChange={handleChange}
                                className="w-full px-4 py-2 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                placeholder="Eve Mipata" required
                            />
                        </div>

                        {/* Field 2: Email */}
                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1.5">Email Address</label>
                            <input
                                type="email" id="email" name="email" disabled={loading} value={formData.email} onChange={handleChange}
                                className="w-full px-4 py-2 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                placeholder="you@example.com" required
                            />
                        </div>

                        {/* Field 3: Business Name */}
                        <div>
                            <label htmlFor="business_name" className="block text-sm font-medium text-slate-300 mb-1.5">Business Name</label>
                            <input
                                type="text" id="business_name" name="business_name" disabled={loading} value={formData.business_name} onChange={handleChange}
                                className="w-full px-4 py-2 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                placeholder="Your Business" required
                            />
                        </div>

                        {/* Field 4: Password */}
                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1.5">Password (min. 8 characters)</label>
                            <input
                                type="password" id="password" name="password" disabled={loading} value={formData.password} onChange={handleChange}
                                className="w-full px-4 py-2 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                placeholder="••••••••" required
                            />
                        </div>

                        {/* Field 5: Confirm Password */}
                        <div>
                            <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300 mb-1.5">Confirm Password</label>
                            <input
                                type="password" id="confirmPassword" name="confirmPassword" disabled={loading} value={formData.confirmPassword} onChange={handleChange}
                                className="w-full px-4 py-2 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                placeholder="••••••••" required
                            />
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