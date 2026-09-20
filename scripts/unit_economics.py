"""Offline planning, not invoices: missing inputs prevent a margin claim."""
import argparse
import json
from decimal import Decimal
from pathlib import Path


def scenarios(config):
    result=[]
    categories=['ai_per_action','social_per_publication','storage_per_user','hosting_per_user','support_per_user','payment_percent','payment_fixed','tax_fraction']
    missing=[k for k in categories if config.get(k) is None]
    values={k:Decimal(str(config[k])) for k in categories if k not in missing}
    if any(not v.is_finite() or v<0 for v in values.values()):raise ValueError('Costs must be finite nonnegative values')
    if values.get('tax_fraction',0)>=1 or values.get('payment_percent',0)>=1:raise ValueError('Use fractions below one for tax and payment percentage')
    for tier,monthly,annual,actions,posts in [('Basic','9.99','99',150,100),('Premium','19.99','199',400,250)]:
        for interval,price in [('monthly',monthly),('annual',annual)]:
            months=Decimal(12 if interval=='annual' else 1)
            gross=Decimal(price)/months
            for name,factor,retries in [('normal',Decimal('.25'),Decimal('1')),('allowance_limit',Decimal(1),Decimal(1)),('failed_and_retried',Decimal(1),Decimal('1.5'))]:
                cost=None;margin=None
                if not missing:
                    cost=actions*factor*retries*values['ai_per_action']+posts*factor*retries*values['social_per_publication']
                    cost+=sum(values[k] for k in ['storage_per_user','hosting_per_user','support_per_user'])
                    cost+=gross*values['payment_percent']+values['payment_fixed']/months
                    margin=gross*(1-values['tax_fraction'])-cost
                result.append({'plan':tier,'interval':interval,'scenario':name,'gross_monthly_gbp':str(gross.quantize(Decimal('.01'))),
                    'estimated_monthly_cost_gbp':str(cost.quantize(Decimal('.01'))) if cost is not None else None,
                    'estimated_contribution_gbp':str(margin.quantize(Decimal('.01'))) if margin is not None else None})
    return {'as_of':config.get('as_of'),'sources':config.get('sources',{}),'missing_inputs':missing,'scenarios':result,
            'caution':'Scenario estimates, not measured margins. Normal assumes 25% of allowance; retry stress assumes 50% additional provider cost. Replace with measured distributions. Excludes acquisition and other fixed business costs.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('config',type=Path)
    args=parser.parse_args();print(json.dumps(scenarios(json.loads(args.config.read_text(encoding='utf-8'))),indent=2))
