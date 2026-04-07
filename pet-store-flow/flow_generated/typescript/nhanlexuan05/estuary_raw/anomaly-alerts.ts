
// Generated for published documents of derived collection nhanlexuan05/estuary_raw/anomaly-alerts.
export type Document = {
    "_meta": {
        uuid: string;
    };
    alert_level?: string;
    amount?: number;
    created_at?: string;
    id: string;
    payment_method?: string;
    product_id?: string;
    transaction_date?: string;
};


// Generated for read documents of sourced collection nhanlexuan05/estuary_raw/txn-clean.
export type SourceFromTxnClean = {
    "_meta": {
        uuid: string;
    };
    amount?: number;
    id: string;
    is_anomaly?: boolean;
    payment_method?: string;
    product_id?: string;
    transaction_date?: string;
    transformed_at?: string;
};


export abstract class IDerivation {
    // Construct a new Derivation instance from a Request.Open message.
    constructor(_open: { state: unknown }) { }

    // flush awaits any remaining documents to be published and returns them.
    // deno-lint-ignore require-await
    async flush(): Promise<Document[]> {
        return [];
    }

    // reset is called only when running catalog tests, and must reset any internal state.
    async reset() { }

    // startCommit is notified of a runtime commit in progress, and returns an optional
    // connector state update to be committed.
    startCommit(_startCommit: { runtimeCheckpoint: unknown }): { state?: { updated: unknown, mergePatch: boolean } } {
        return {};
    }

    abstract fromTxnClean(read: { doc: SourceFromTxnClean }): Document[];
}
