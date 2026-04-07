
// Generated for published documents of derived collection nhanlexuan05/estuary_raw/reviews-enriched.
export type Document = {
    "_meta": {
        uuid: string;
    };
    id: string;
    product_id?: string;
    rating?: number;
    review_text?: string;
    review_time?: string;
    sentiment?: string;
    transformed_at?: string;
};


// Generated for read documents of sourced collection nhanlexuan05/estuary_raw/estuary_raw/reviews.
export type SourceFromReviews = {
    "_id"?: unknown;
    "_meta": {
        uuid: string;
    };
    product_id?: string;
    rating?: number;
    review_text?: string;
    review_time?: unknown;
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

    abstract fromReviews(read: { doc: SourceFromReviews }): Document[];
}
