# -*- coding: utf-8 -*-
"""

Created on Fri Oct 04 13:19:01 2013

Author: Josef Perktold
"""

import numpy as np
from numpy.testing import assert_allclose, assert_almost_equal, assert_equal

from statsmodels import iolib
from statsmodels.tools.tools import add_constant
from statsmodels.regression.linear_model import OLS
import statsmodels.sandbox.regression.gmm as gmm

def get_griliches76_data():
    import os
    curdir = os.path.split(__file__)[0]
    path = os.path.join(curdir, 'griliches76.dta')
    griliches76_data = iolib.genfromdta(path, missing_flt=np.NaN, pandas=True)

    # create year dummies
    years = griliches76_data['year'].unique()
    N = griliches76_data.shape[0]

    for yr in years:
        griliches76_data['D_%i' %yr] = np.zeros(N)
        for i in range(N):
            if griliches76_data['year'][i] == yr:
                griliches76_data['D_%i' %yr][i] = 1
            else:
                pass

    griliches76_data['const'] = 1

    X = add_constant(griliches76_data[['s', 'iq', 'expr', 'tenure', 'rns',
                                       'smsa', 'D_67', 'D_68', 'D_69', 'D_70',
                                       'D_71', 'D_73']],
                                       prepend=True)  # for R comparison
                                       #prepend=False)  # for Stata comparison

    Z = add_constant(griliches76_data[['expr', 'tenure', 'rns', 'smsa', \
                                       'D_67', 'D_68', 'D_69', 'D_70', 'D_71',
                                       'D_73', 'med', 'kww', 'age', 'mrt']])
    Y = griliches76_data['lw']

    return Y, X, Z

# use module global to load only once
yg_df, xg_df, zg_df = get_griliches76_data()

endog = np.asarray(yg_df, dtype=float)  # TODO: why is yg_df float32
exog, instrument = map(np.asarray, [xg_df, zg_df])

assert exog.dtype == np.float64
assert instrument.dtype == np.float64


# from R
#-----------------
varnames = np.array(["(Intercept)", "s", "iq", "expr", "tenure", "rns", "smsa", "D_67", "D_68", "D_69", "D_70",
       "D_71", "D_73"])
params = np.array([ 4.03350989,  0.17242531, -0.00909883,  0.04928949,  0.04221709,
       -0.10179345,  0.12611095, -0.05961711,  0.04867956,  0.15281763,
        0.17443605,  0.09166597,  0.09323977])
bse = np.array([ 0.31816162,  0.02091823,  0.00474527,  0.00822543,  0.00891969,
        0.03447337,  0.03119615,  0.05577582,  0.05246796,  0.05201092,
        0.06027671,  0.05461436,  0.05767865])
tvalues = np.array([ 12.6775501,   8.2428242,  -1.9174531,   5.9923305,   4.7330205,
        -2.9528144,   4.0425165,  -1.0688701,   0.9277959,   2.9381834,
         2.8939212,   1.6784225,   1.6165385])
pvalues = np.array([  1.72360000e-33,   7.57025400e-16,   5.55625000e-02,
         3.21996700e-09,   2.64739100e-06,   3.24794100e-03,
         5.83809900e-05,   2.85474400e-01,   3.53813900e-01,
         3.40336100e-03,   3.91575100e-03,   9.36840200e-02,
         1.06401300e-01])
    #-----------------

def test_iv2sls_r():

    mod = gmm.IV2SLS(endog, exog, instrument)
    res = mod.fit()

    # print res.params
    # print res.params - params

    n, k = exog.shape

    assert_allclose(res.params, params, rtol=1e-7, atol=1e-9)
    # TODO: check df correction
    #assert_allclose(res.bse * np.sqrt((n - k) / (n - k - 1.)), bse,
    assert_allclose(res.bse, bse, rtol=0, atol=3e-7)



def test_ivgmm0_r():
    n, k = exog.shape
    nobs, k_instr = instrument.shape

    w0inv = np.dot(instrument.T, instrument) / nobs
    w0 = np.linalg.inv(w0inv)

    mod = gmm.IVGMM(endog, exog, instrument)
    res = mod.fit(np.ones(exog.shape[1], float), maxiter=0, inv_weights=w0inv,
                  optim_method='bfgs',
                  optim_args={'gtol':1e-8, 'disp': 0})


    assert_allclose(res.params, params, rtol=1e-4, atol=1e-4)
    # TODO : res.bse and bse are not the same, rtol=0.09 is large in this case
    #res.bse is still robust?, bse is not a sandwich ?
    assert_allclose(res.bse, bse, rtol=0.09, atol=0)

    score = res.model.score(res.params, w0)
    assert_allclose(score, np.zeros(score.shape), rtol=0, atol=5e-6) # atol=1e-8) ??


def test_ivgmm1_stata():

    # copied constant to the beginning
    params_stata = np.array(
          [ 4.0335099 ,  0.17242531, -0.00909883,  0.04928949,  0.04221709,
           -0.10179345,  0.12611095, -0.05961711,  0.04867956,  0.15281763,
            0.17443605,  0.09166597,  0.09323976])

    # robust bse with gmm onestep
    bse_stata = np.array(
          [ 0.33503289,  0.02073947,  0.00488624,  0.0080498 ,  0.00946363,
            0.03371053,  0.03081138,  0.05171372,  0.04981322,  0.0479285 ,
            0.06112515,  0.0554618 ,  0.06084901])

    n, k = exog.shape
    nobs, k_instr = instrument.shape

    w0inv = np.dot(instrument.T, instrument) / nobs
    w0 = np.linalg.inv(w0inv)
    start = OLS(endog, exog).fit().params

    mod = gmm.IVGMM(endog, exog, instrument)
    res = mod.fit(start, maxiter=1, inv_weights=w0inv, optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0})


# move constant to end for Stata
idx = range(len(params))
idx = idx[1:] + idx[:1]
exog_st = exog[:, idx]


class TestGMMOLS(object):

    @classmethod
    def setup_class(self):
        exog = exog_st  # with const at end
        res_ols = OLS(endog, exog).fit()

        #  use exog as instrument
        nobs, k_instr = exog.shape
        w0inv = np.dot(exog.T, exog) / nobs
        #w0 = np.linalg.inv(w0inv)

        mod = gmm.IVGMM(endog, exog, exog)
        res = mod.fit(np.ones(exog.shape[1], float), maxiter=0, inv_weights=w0inv,
                        optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0})

        self.res1 = res
        self.res2 = res_ols


    def test_basic(self):
        res1, res2 = self.res1, self.res2
        # test both absolute and relative difference
        assert_allclose(res1.params, res2.params, rtol=5e-4, atol=0)
        assert_allclose(res1.params, res2.params, rtol=0, atol=1e-5)

        n = res1.model.exog.shape[0]
        dffac = 1#np.sqrt((n - 1.) / n)   # currently different df in cov calculation
        assert_allclose(res1.bse * dffac, res2.HC0_se, rtol=5e-6, atol=0)
        assert_allclose(res1.bse * dffac, res2.HC0_se, rtol=0, atol=1e-7)


    def test_other(self):
        res1, res2 = self.res1, self.res2




class CheckGMM(object):

    params_tol = [5e-6, 5e-6]
    bse_tol = [5e-7, 5e-7]

    def test_basic(self):
        res1, res2 = self.res1, self.res2
        # test both absolute and relative difference
        rtol,  atol = self.params_tol
        assert_allclose(res1.params, res2.params, rtol=rtol, atol=0)
        assert_allclose(res1.params, res2.params, rtol=0, atol=atol)

        n = res1.model.exog.shape[0]
        dffac = 1 #np.sqrt((n - 1.) / n)   # currently different df in cov calculation
        rtol,  atol = self.bse_tol
        assert_allclose(res1.bse * dffac, res2.bse, rtol=rtol, atol=0)
        assert_allclose(res1.bse * dffac, res2.bse, rtol=0, atol=atol)

    #skip temporarily
    def _est_other(self):
        res1, res2 = self.res1, self.res2
        assert_allclose(res1.q, res2.Q, rtol=5e-6, atol=0)
        assert_allclose(res1.jval, res2.J, rtol=5e-5, atol=0)



class TestGMMSt1(CheckGMM):

    @classmethod
    def setup_class(self):
        #self.bse_tol = [5e-7, 5e-7]
        # compare to Stata default options, iterative GMM
        exog = exog_st  # with const at end
        start = OLS(endog, exog).fit().params
        nobs, k_instr = instrument.shape
        w0inv = np.dot(instrument.T, instrument) / nobs
        #w0 = np.linalg.inv(w0inv)

        mod = gmm.IVGMM(endog, exog, instrument)
        res10 = mod.fit(start, maxiter=10, inv_weights=w0inv,
                        optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0},
                        wargs={'centered':False})
        self.res1 = res10

        from results_gmm_griliches_iter import results
        self.res2 = results

class TestGMMStTwostep(CheckGMM):
    #compares has_optimal_weights=True with Stata's has_optimal_weights=False

    @classmethod
    def setup_class(self):
        # compare to Stata default options, twostep GMM
        self.params_tol = [5e-5, 5e-6]
        self.bse_tol = [5e-6, 5e-7]
        exog = exog_st  # with const at end
        start = OLS(endog, exog).fit().params
        nobs, k_instr = instrument.shape
        w0inv = np.dot(instrument.T, instrument) / nobs
        #w0 = np.linalg.inv(w0inv)

        mod = gmm.IVGMM(endog, exog, instrument)
        res10 = mod.fit(start, maxiter=2, inv_weights=w0inv,
                        optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0},
                        wargs={'centered':False})
        self.res1 = res10

        from results_gmm_griliches import results_twostep as results
        self.res2 = results


class TestGMMStTwostepNO(CheckGMM):
    #with Stata default `has_optimal_weights=False`

    @classmethod
    def setup_class(self):
        # compare to Stata default options, twostep GMM
        self.params_tol = [5e-5, 5e-6]
        self.bse_tol = [1e-6, 5e-5]
        exog = exog_st  # with const at end
        start = OLS(endog, exog).fit().params
        nobs, k_instr = instrument.shape
        w0inv = np.dot(instrument.T, instrument) / nobs
        #w0 = np.linalg.inv(w0inv)

        mod = gmm.IVGMM(endog, exog, instrument)
        res10 = mod.fit(start, maxiter=2, inv_weights=w0inv,
                        optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0},
                        wargs={'centered':False}, has_optimal_weights=False)
        self.res1 = res10

        from results_gmm_griliches import results_twostep as results
        self.res2 = results


class TestGMMStOnestep(CheckGMM):

    @classmethod
    def setup_class(self):
        # compare to Stata default options, onestep GMM
        self.params_tol = [5e-4, 5e-5]
        self.bse_tol = [7e-3, 5e-4]
        exog = exog_st  # with const at end
        start = OLS(endog, exog).fit().params
        nobs, k_instr = instrument.shape
        w0inv = np.dot(instrument.T, instrument) / nobs
        #w0 = np.linalg.inv(w0inv)

        mod = gmm.IVGMM(endog, exog, instrument)
        res = mod.fit(start, maxiter=0, inv_weights=w0inv,
                        optim_method='bfgs',
                        optim_args={'gtol':1e-6, 'disp': 0})
        self.res1 = res

        from results_gmm_griliches import results_onestep as results
        self.res2 = results

    def test_bse_other(self):
        res1, res2 = self.res1, self.res2
        # try other versions for bse,
        # TODO: next two produce the same as before (looks like)
        bse = np.sqrt(np.diag((res1.cov_params(has_optimal_weights=False))))
                                            #weights=res1.weights))))
        # TODO: doesn't look different
        #assert_allclose(res1.bse, res2.bse, rtol=5e-06, atol=0)
        #nobs = instrument.shape[0]
        #w0inv = np.dot(instrument.T, instrument) / nobs
        q = self.res1.model.gmmobjective(self.res1.params, np.linalg.inv(self.res1.weights))
        #assert_allclose(q, res2.Q, rtol=5e-6, atol=0)

class TestGMMStOnestepNO(CheckGMM):
    # matches Stats's defaults wargs={'centered':False}, has_optimal_weights=False

    @classmethod
    def setup_class(self):
        # compare to Stata default options, onestep GMM
        self.params_tol = [1e-5, 1e-6]
        self.bse_tol = [5e-6, 5e-7]
        exog = exog_st  # with const at end
        start = OLS(endog, exog).fit().params
        nobs, k_instr = instrument.shape
        w0inv = np.dot(instrument.T, instrument) / nobs
        #w0 = np.linalg.inv(w0inv)

        mod = gmm.IVGMM(endog, exog, instrument)
        res = mod.fit(start, maxiter=0, inv_weights=w0inv,
                        optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0},
                        wargs={'centered':False}, has_optimal_weights=False)
        self.res1 = res

        from results_gmm_griliches import results_onestep as results
        self.res2 = results

class TestGMMStOneiter(CheckGMM):

    @classmethod
    def setup_class(self):
        # compare to Stata default options, onestep GMM
        # this uses maxiter=1, one iteration in loop
        self.params_tol = [5e-4, 5e-5]
        self.bse_tol = [7e-3, 5e-4]
        exog = exog_st  # with const at end
        start = OLS(endog, exog).fit().params
        nobs, k_instr = instrument.shape
        w0inv = np.dot(instrument.T, instrument) / nobs
        #w0 = np.linalg.inv(w0inv)

        mod = gmm.IVGMM(endog, exog, instrument)
        res = mod.fit(start, maxiter=1, inv_weights=w0inv,
                        optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0})
        self.res1 = res

        from results_gmm_griliches import results_onestep as results
        self.res2 = results


    def test_bse_other(self):
        res1, res2 = self.res1, self.res2

        moms = res1.model.momcond(res1.params)
        w = res1.model.calc_weightmatrix(moms)
        # try other versions for bse,
        # TODO: next two produce the same as before (looks like)
        bse = np.sqrt(np.diag((res1.cov_params(has_optimal_weights=False,
                                            weights=res1.weights))))
        # TODO: doesn't look different
        #assert_allclose(res1.bse, res2.bse, rtol=5e-06, atol=0)
        bse = np.sqrt(np.diag((res1.cov_params(has_optimal_weights=False,
                                               #use_weights=True #weights=w
                                                         ))))
        #assert_allclose(res1.bse, res2.bse, rtol=5e-06, atol=0)

        #This doesn't replicate Stata oneway either
        nobs = instrument.shape[0]
        w0inv = np.dot(instrument.T, instrument) / nobs
        q = self.res1.model.gmmobjective(self.res1.params, w)#self.res1.weights)
        #assert_allclose(q, res2.Q, rtol=5e-6, atol=0)


class TestGMMStOneiterNO(CheckGMM):

    @classmethod
    def setup_class(self):
        # compare to Stata default options, onestep GMM
        # this uses maxiter=1, one iteration in loop
        self.params_tol = [1e-5, 1e-6]
        self.bse_tol = [5e-6, 5e-7]
        exog = exog_st  # with const at end
        start = OLS(endog, exog).fit().params
        nobs, k_instr = instrument.shape
        w0inv = np.dot(instrument.T, instrument) / nobs
        #w0 = np.linalg.inv(w0inv)

        mod = gmm.IVGMM(endog, exog, instrument)
        res = mod.fit(start, maxiter=1, inv_weights=w0inv,
                        optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0},
                        wargs={'centered':False}, has_optimal_weights=False)
        self.res1 = res

        from results_gmm_griliches import results_onestep as results
        self.res2 = results


#------------ Crosscheck subclasses

class TestGMMStOneiterNO_Linear(CheckGMM):

    @classmethod
    def setup_class(self):
        # compare to Stata default options, onestep GMM
        # this uses maxiter=1, one iteration in loop
        self.params_tol = [5e-9, 1e-9]
        self.bse_tol = [5e-10, 1e-10]
        exog = exog_st  # with const at end
        start = OLS(endog, exog).fit().params
        nobs, k_instr = instrument.shape
        w0inv = np.dot(instrument.T, instrument) / nobs
        #w0 = np.linalg.inv(w0inv)

        mod = gmm.LinearIVGMM(endog, exog, instrument)
        res = mod.fit(start, maxiter=1, inv_weights=w0inv,
                        optim_method='bfgs', optim_args={'gtol':1e-8, 'disp': 0},
                        wargs={'centered':False}, has_optimal_weights=False)
        self.res1 = res

        mod = gmm.IVGMM(endog, exog, instrument)
        res = mod.fit(start, maxiter=1, inv_weights=w0inv,
                        optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0},
                        wargs={'centered':False}, has_optimal_weights=False)
        self.res3 = res

        from results_gmm_griliches import results_onestep as results
        self.res2 = results


class TestGMMStOneiterNO_Nonlinear(CheckGMM):

    @classmethod
    def setup_class(self):
        # compare to Stata default options, onestep GMM
        # this uses maxiter=1, one iteration in loop
        self.params_tol = [5e-5, 5e-6]
        self.bse_tol = [5e-6, 1e-1]
        exog = exog_st  # with const at end
        start = OLS(endog, exog).fit().params
        nobs, k_instr = instrument.shape
        w0inv = np.dot(instrument.T, instrument) / nobs
        #w0 = np.linalg.inv(w0inv)

        def func(params, exog):
            return np.dot(exog, params)

        mod = gmm.NonlinearIVGMM(endog, exog, instrument, func)
        res = mod.fit(start, maxiter=1, inv_weights=w0inv,
                        optim_method='bfgs', optim_args={'gtol':1e-8, 'disp': 0},
                        wargs={'centered':False}, has_optimal_weights=False)
        self.res1 = res

        mod = gmm.IVGMM(endog, exog, instrument)
        res = mod.fit(start, maxiter=1, inv_weights=w0inv,
                        optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0},
                        wargs={'centered':False}, has_optimal_weights=False)
        self.res3 = res

        from results_gmm_griliches import results_onestep as results
        self.res2 = results


    def test_score(self):
        params = self.res1.params * 1.1
        weights = self.res1.weights
        sc1 = self.res1.model.score(params, weights)
        sc2 = super(self.res1.model.__class__, self.res1.model).score(params,
                                                                      weights)
        assert_allclose(sc1, sc2, rtol=1e-6, atol=0)
        assert_allclose(sc1, sc2, rtol=0, atol=1e-7)

        # score at optimum
        sc1 = self.res1.model.score(self.res1.params, weights)
        assert_allclose(sc1, np.zeros(len(params)), rtol=0, atol=1e-8)



class TestGMMStOneiterOLS_Linear(CheckGMM):

    @classmethod
    def setup_class(self):
        # replicating OLS by GMM - high agreement
        self.params_tol = [1e-11, 1e-12]
        self.bse_tol = [1e-13, 1e-13]
        exog = exog_st  # with const at end
        res_ols = OLS(endog, exog).fit()
        #Note: start is irrelevant but required
        start = np.ones(len(res_ols.params))
        nobs, k_instr = instrument.shape
        w0inv = np.dot(exog.T, exog) / nobs
        #w0 = np.linalg.inv(w0inv)

        mod = gmm.LinearIVGMM(endog, exog, exog)
        res = mod.fit(start, maxiter=0, inv_weights=w0inv,
                        #optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0},
                        optim_args={'disp': 0},
                        weights_method='iid',
                        wargs={'centered':False, 'ddof':'k_params'},
                        has_optimal_weights=True)
        self.res1 = res

        #from results_gmm_griliches import results_onestep as results
        #self.res2 = results
        self.res2 = res_ols


#------------------

class TestGMMSt2(object):
    # this looks like an old version, trying out different comparisons
    # of options with Stats

    @classmethod
    def setup_class(self):
        # compare to Stata default options, iterative GMM
        exog = exog_st  # with const at end
        start = OLS(endog, exog).fit().params
        nobs, k_instr = instrument.shape
        w0inv = np.dot(instrument.T, instrument) / nobs
        #w0 = np.linalg.inv(w0inv)

        mod = gmm.IVGMM(endog, exog, instrument)
        res = mod.fit(start, maxiter=2, inv_weights=w0inv,
                      wargs={'ddof':0, 'centered':False},
                      optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0})
        self.res1 = res

        from results_ivreg2_griliches import results_gmm2s_robust as results
        self.res2 = results

        # TODO: remove after testing, compare bse from 1 iteration
        # see test_basic
        mod = gmm.IVGMM(endog, exog, instrument)
        res = mod.fit(start, maxiter=1, inv_weights=w0inv,
                      wargs={'ddof':0, 'centered':False},
                      optim_method='bfgs', optim_args={'gtol':1e-6, 'disp': 0})
        self.res3 = res


    def test_basic(self):
        res1, res2 = self.res1, self.res2
        # test both absolute and relative difference
        assert_allclose(res1.params, res2.params, rtol=5e-05, atol=0)
        assert_allclose(res1.params, res2.params, rtol=0, atol=5e-06)

        n = res1.model.exog.shape[0]
        # TODO: check df correction np.sqrt(745./758 )*res1.bse matches better
        dffact = np.sqrt(745. / 758 )
        assert_allclose(res1.bse * dffact, res2.bse, rtol=5e-03, atol=0)
        assert_allclose(res1.bse * dffact, res2.bse, rtol=0, atol=5e-03)

        # try other versions for bse,
        # TODO: next two produce the same as before (looks like)
        bse = np.sqrt(np.diag((res1.cov_params(has_optimal_weights=True,
                                            weights=res1.weights))))
        assert_allclose(res1.bse, res2.bse, rtol=5e-01, atol=0)

        bse = np.sqrt(np.diag((res1.cov_params(has_optimal_weights=True,
                                               weights=res1.weights,
                                               use_weights=True))))
        assert_allclose(res1.bse, res2.bse, rtol=5e-02, atol=0)

        # TODO: resolve this
        # try bse from previous step, is closer to Stata
        # guess: Stata ivreg2 doesn't calc for bse update after final iteration
        # need better test case, bse difference is close to numerical optimization precision
        assert_allclose(self.res3.bse, res2.bse, rtol=5e-05, atol=0)
        assert_allclose(self.res3.bse, res2.bse, rtol=0, atol=5e-06)



        # TODO; tvalues are not available yet, no inheritance
        #assert_allclose(res1.tvalues, res2.tvalues, rtol=5e-10, atol=0)




class CheckIV2SLS(object):

    def test_basic(self):
        res1, res2 = self.res1, self.res2
        # test both absolute and relative difference
        assert_allclose(res1.params, res2.params, rtol=1e-9, atol=0)
        assert_allclose(res1.params, res2.params, rtol=0, atol=1e-10)

        n = res1.model.exog.shape[0]
        assert_allclose(res1.bse, res2.bse, rtol=1e-10, atol=0)
        assert_allclose(res1.bse, res2.bse, rtol=0, atol=1e-11)

        assert_allclose(res1.tvalues, res2.tvalues, rtol=5e-10, atol=0)


    def test_other(self):
        res1, res2 = self.res1, self.res2
        assert_allclose(res1.rsquared, res2.r2, rtol=1e-7, atol=0)
        assert_allclose(res1.rsquared_adj, res2.r2_a, rtol=1e-7, atol=0)

        # TODO: why is fvalue different, IV2SLS uses inherited linear
        assert_allclose(res1.fvalue, res2.F, rtol=1e-10, atol=0)
        assert_allclose(res1.f_pvalue, res2.Fp, rtol=1e-8, atol=0)
        assert_allclose(np.sqrt(res1.mse_resid), res2.rmse, rtol=1e-10, atol=0)
        assert_allclose(res1.ssr, res2.rss, rtol=1e-10, atol=0)
        assert_allclose(res1.uncentered_tss, res2.yy, rtol=1e-10, atol=0)
        assert_allclose(res1.centered_tss, res2.yyc, rtol=1e-10, atol=0)
        assert_allclose(res1.ess, res2.mss, rtol=1e-9, atol=0)

        assert_equal(res1.df_model, res2.df_m)
        assert_equal(res1.df_resid, res2.df_r)

        # TODO: llf raise NotImplementedError
        #assert_allclose(res1.llf, res2.ll, rtol=1e-10, atol=0)


    def test_hypothesis(self):
        res1, res2 = self.res1, self.res2
        restriction = np.eye(len(res1.params))
        res_t = res1.t_test(restriction)
        assert_allclose(res_t.tvalue, res1.tvalues, rtol=1e-12, atol=0)
        assert_allclose(res_t.pvalue, res1.pvalues, rtol=1e-12, atol=0)
        res_f = res1.f_test(restriction[:-1]) # without constant
        # TODO res1.fvalue problem, see issue #1104
        assert_allclose(res_f.fvalue, res1.fvalue, rtol=1e-12, atol=0)
        assert_allclose(res_f.pvalue, res1.f_pvalue, rtol=1e-12, atol=0)
        assert_allclose(res_f.fvalue, res2.F, rtol=1e-10, atol=0)
        assert_allclose(res_f.pvalue, res2.Fp, rtol=1e-08, atol=0)


    def test_hausman(self):
        res1, res2 = self.res1, self.res2
        hausm = res1.spec_hausman()
        # hausman uses se2 = ssr / nobs, no df correction
        assert_allclose(hausm[0], res2.hausman['DWH'], rtol=1e-11, atol=0)
        assert_allclose(hausm[1], res2.hausman['DWHp'], rtol=1e-10, atol=0)


    def test_smoke(self):
        res1 = self.res1
        res1.summary()



class TestIV2SLSSt1(CheckIV2SLS):

    @classmethod
    def setup_class(self):
        exog = exog_st  # with const at end
        start = OLS(endog, exog).fit().params
        nobs, k_instr = instrument.shape

        mod = gmm.IV2SLS(endog, exog, instrument)
        res = mod.fit()
        self.res1 = res

        from results_ivreg2_griliches import results_small as results
        self.res2 = results
