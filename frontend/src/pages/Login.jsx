//========================================================================
//  LOGIN INTERACTIVE USER VISUAL FORM
//========================================================================

import { useState } from 'react';  //memory box and must be at the very top opf the file
import { useNavigate, useLocation, Link} from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

// const tells the computer: "Create a labeled box for this data, and never let its name or purpose change."s
export default function Login() {
const navigate = useNavigate();  //force switch pages programatcally
const location = useLocation(); //get current location page
const { login, loading, error } = useAuth();

const [ formData, setFormData ] = useState({
    email: '',
    password: ''
});
const [ formErrors, setFormErrors ] = useState('');
const targetRedirectPath = location.state?.from?.pathname || '/overview';

//triggered when the user types in the form fields, updates the formData state with the new values, and clears any existing form errors.    (e stand for event)
const handleChange = (e) => {
    setFormData((prev) => ({
        ...prev,
        [e.target.name]: e.target.value
    }));
    setFormErrors('');
};

//===============================================================================================
//FORM SUBMISSION AND BACKEND COORDINATION
//===============================================================================================
const handleSubmit = async (e) => {
    e.preventDefault();  //stop the browser from refreshin the page  when the form is submitted
    setFormErrors('');

    if (!formData.email || !formData.password) {
        setFormErrors('email and password required');
        return;
    }
    try {
        await login(formData);
        navigate (targetRedirectPath , { replace: true });  //redirect to the target page after successful login
    } catch (err) {
        setFormErrors(err.message || 'Invalid credentials');
    }
};

return (
    //Base Layout wrapper: Dark- slate diagonal gradient , centers  the card prefectly on the screen
    <div className= "min-h-screen  bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4">
        <div className="w-full max-w-md">

            {/*Application Brand header*/}
            <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg mb-4 shadow-orange-500/10">
                {/* AISHA AI Brand Logo SVG Icon */}
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">AISHA AI</h1>
          <p className="text-slate-400 font-medium">AI Sales Assistant</p>
        </div>

        {/* The Card Box Container */}
        <div className="bg-slate-800 rounded-xl shadow-2xl border border-slate-700/60 p-8">
          <h2 className="text-xl font-semibold text-white mb-6">Welcome Back</h2>

        {/* DYNAMIC ERROR CONDITIONAL PANEL */}
          {/* If there is a local form layout error OR a backend server connection error, show this block */}
          {(formErrors || error) && (
            <div className="mb-5 p-3.5 bg-red-900/30 border border-red-700/40 rounded-lg">
              <p className="text-red-400 text-sm font-medium">{formErrors || error}</p>
            </div>
          )}

          {/* Interactive Input Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-2">Email Address</label>
              <input
                type="email" id="email" name="email" 
                disabled={loading} // Freeze field if backend request is processing
                value={formData.email} onChange={handleChange}
                className="w-full px-4 py-2.5 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                placeholder="you@example.com" required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-2">Password</label>
              <input
                type="password" id="password" name="password" 
                disabled={loading} // Freeze field if backend request is processing
                value={formData.password} onChange={handleChange}
                className="w-full px-4 py-2.5 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                placeholder="••••••••" required
              />
            </div>

            {/* Submit Action Button */}
            <button
              type="submit" disabled={loading}
              className="w-full flex items-center justify-center bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold py-2.5 rounded-lg hover:from-orange-600 hover:to-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500/50 transition disabled:opacity-50 mt-2"
            >
              {/* If busy, text swaps to status; otherwise defaults to Sign In */}
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>

          {/* Separation Divider Layer */}
          <div className="my-6 relative">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-600/80"></div></div>
            <div className="relative flex justify-center text-sm"><span className="px-3 bg-slate-800 text-slate-400 font-medium">Don't have an account?</span></div>
          </div>

          {/* Navigation Link to Signup Form */}
          <Link to="/signup" className="block w-full text-center px-4 py-2.5 border border-slate-600 text-slate-300 font-semibold rounded-lg hover:bg-slate-700/40 hover:border-slate-500 transition">
            Create Account
          </Link>
        </div>
      </div>
    </div>
    );
    }
