import argparse

def calculate_futures_pnl(entry_price, mark_price, notional_value_usdt, leverage, margin_usdt, position_type='short'):
    """
    Calculate Unrealized PNL and ROI% for Binance Futures positions.
    """
    # Convert notional value to base asset size
    position_size_base = notional_value_usdt / entry_price

    if position_type == 'long':
        pnl = (mark_price - entry_price) * position_size_base
    elif position_type == 'short':
        pnl = (entry_price - mark_price) * position_size_base
    else:
        raise ValueError("position_type must be either 'long' or 'short'")

    roi_percent = (pnl / margin_usdt) * 100 if margin_usdt != 0 else 0

    return {
        'PNL (USDT)': round(pnl, 4),
        'ROI (%)': round(roi_percent, 4)
    }

def main():
    parser = argparse.ArgumentParser(description="Calculate Binance Futures PNL and ROI.")
    parser.add_argument('--entry', type=float, required=True, help="Entry price")
    parser.add_argument('--mark', type=float, required=True, help="Current mark price")
    parser.add_argument('--notional', type=float, required=True, help="Position size in USDT")
    parser.add_argument('--leverage', type=float, required=True, help="Leverage used")
    parser.add_argument('--margin', type=float, required=True, help="Isolated margin in USDT")
    parser.add_argument('--type', choices=['long', 'short'], default='short', help="Position type")

    args = parser.parse_args()

    result = calculate_futures_pnl(
        entry_price=args.entry,
        mark_price=args.mark,
        notional_value_usdt=args.notional,
        leverage=args.leverage,
        margin_usdt=args.margin,
        position_type=args.type
    )

    print("\n=== Binance Futures PNL Calculation ===")
    print(f"PNL: {result['PNL (USDT)']} USDT")
    print(f"ROI: {result['ROI (%)']}%")

if __name__ == '__main__':
    main()

